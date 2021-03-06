import os
import smtplib
import ssl
from datetime import timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytz
import regex as re
from slack_sdk.webhook import WebhookClient
import requests
from timeloop import Timeloop
from SlidingWindowMap import SlidingWindowMap
from logger import logger
from config import *

webhook = WebhookClient(slack_url)
job_loop = Timeloop()
# double the size of the map because sometimes posts are removed from reddit, leading to
# old posts being reincluded in the search query
most_recent_posts = SlidingWindowMap(2 * search_result_limit)


def main():
    # auth not needed for search
    # headers = authenticate_reddit()

    # compile regexp for search
    global coarse_regex
    global fine_regex
    global title_regex
    global price_regex
    coarse_regex = compile_re(coarse_regex)
    fine_regex = compile_re(fine_regex)
    title_regex = compile_re(title_regex)
    price_regex = compile_re(price_regex)

    # pre populate new posts queuemap to notify only for stuff posted after the program is started
    find_newest()
    # start the job loop to continuously check for new posts
    job_loop.start(block=True)


@job_loop.job(interval=timedelta(seconds=post_update_interval_seconds))
def update_search():
    new_post_keys = find_newest()
    # filter out the posts we want using regex
    coarse_keys = regex_filter(new_post_keys, coarse_regex)
    fine_keys = regex_filter(coarse_keys, fine_regex)
    coarse_keys = coarse_keys - fine_keys
    get_title = lambda posts: "{} new match{} found".format(len(posts), "es" if len(posts) > 1 else "")
    if coarse_keys or fine_keys:
        notify(coarse_keys, "COARSE - {}".format(get_title(coarse_keys)))
        notify(fine_keys, "FINE - {}".format(get_title(fine_keys)))
    print(f"\t\t{len(coarse_keys)}/{len(new_post_keys)} coarse matches")
    print(f"\t\t{len(fine_keys)}/{len(new_post_keys)} fine matches")


def find_newest():
    curr_time = datetime.now().strftime("%D %H:%M:%S")
    print(f"[{curr_time}] Rerunning search...")
    new_keys = set()

    try:
        res = search_reddit(subreddit, search_string) if search_string else retrieve_all(subreddit)
        updated_posts = parse_search(res)
        # only save keys for the post and use the most_recent map to get the actual post
        # to save time/space
        for post in updated_posts:
            # if the key was successfully added we know it "pushed" another one out of its spot
            # therefore its a new post
            title = post['title']
            if most_recent_posts.put(title, post):
                new_keys.add(title)
        print("\t\t{}/{} are new posts".format(len(new_keys), len(updated_posts)))

    except AssertionError as e:  # catch all exceptions because we want to keep running even if theres a failure
        logger.error(msg=f"Error searching reddit: {e}")
    return new_keys


def notify(post_keys, title):
    if post_keys:
        # send a slack message/email if there are new posts
        # email_message = create_email(new_posts)
        # send the notification
        try:
            notify_slack(post_keys, title)
            print(f"\tSlack message sent to: {slack_url}")

            # send_email(email_message)
            # print("Email sent to: {} from: {}".format(receiver_email, sender_email))
        except AssertionError as e:
            logger.error(msg=f"Error sending notification: {e}")

    """
    # refresh the auth token before it expires
    @loop.job(interval=timedelta(minutes=50))
    def refresh_token():
        global headers
        headers = authenticate_reddit()
"""


def notify_slack(post_keys, title):
    curr_time = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    # make a list of the new posts in markdown
    msg_bodies = []
    for k in post_keys:
        post_data = most_recent_posts.get(k)
        delta = datetime.now(tz=pytz.utc) - post_data['created_utc']
        body = "*<{}|{}>*\nNotified in {} seconds\n\n".format(
            post_data['url'],
            post_data['title'],
            round(delta.total_seconds(), 2),
        )

        # add the prices we found
        prices = "".join([f"Price: {match.group('gpu')} {match.group('price')}\n"
                          for match in re.finditer(price_regex, post_data['body'])])

        msg_bodies.append(body + prices)

    text = f"[{curr_time}] {title}\n" \
           + "\n\n".join(msg_bodies)

    blocks = [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }]

    # send the slack message
    response = webhook.send(
        text=title,
        blocks=blocks
    )

    assert response.status_code == 200, f"{response.status_code} received from Slack"
    assert response.body == "ok", f"{response.body} received from Slack"


def search_reddit(subreddit, search_string):
    # query newest posts from a search result
    headers = {'User-Agent': user_agent}
    # small search result limit to reduce randomness of queries that return a large amount of results
    params = {'q': search_string, 'limit': str(search_result_limit), 'sort': 'new', 't': 'week', 'restrict_sr': 'true'}
    try:
        res = requests.get(f"https://reddit.com/r/{subreddit}/search.json", params=params, headers=headers)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching reddit: {e}")
    assert res.status_code == 200, f"{res.status_code} received from reddit"
    return res


def retrieve_all(subreddit):
    # query all newest posts in a subreddit
    headers = {'User-Agent': user_agent}
    res = requests.get(f"https://reddit.com/r/{subreddit}/new.json", headers=headers)
    assert res.status_code == 200, f"{res.status_code} received from reddit"
    return res


def parse_search(search_response):
    # build a list of dicts from the search results
    # you can use pandas read from dict but it gets messy with nested dicts/json
    posts = []
    for i, post in enumerate(search_response.json()['data']['children']):
        # extract only stuff from post that we need
        data = {
            'title': post['data']['title'],
            'body': post['data']['selftext'],
            'flair': post['data']['link_flair_text'],
            'url': post['data']['url'],
            'created_utc': datetime.fromtimestamp(post['data']['created_utc'], tz=pytz.utc)
        }
        posts.append(data)

    # filter to only posts that are selling
    # filtering by flair can be slow because people forget to flair, then the post isn't marked selling until
    # the bot tags it, and by that point the stuff has already been sold
    # use regex to filter out posts that "seem" to be selling, i.e. accepting paypal in the title
    # this also helps to filter out posts that are local only
    # posts = filter(lambda data: data['flair'] == 'SELLING', posts)
    title_filtered = [p for p in posts if re.findall(title_regex, p['title'])]
    print("\t{}/{} posts matching title filters".format(len(title_filtered), len(posts)))
    return title_filtered


def regex_filter(post_keys, reg_exp):
    matching_posts_keys = set()
    for key in post_keys:
        post = most_recent_posts.get(key)
        matches = re.findall(reg_exp, post['title'] + post['body'])
        if matches:
            matching_posts_keys.add(key)
    return matching_posts_keys


def send_email(message):
    port = 465  # For gmail SSL

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message)


def authenticate_reddit():
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    # note that CLIENT_ID refers to 'personal use script' and SECRET_TOKEN to 'secret' on reddit.com
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)

    # here we pass our login method (password), username, and password
    data = {'grant_type': 'password',
            'username': username,
            'password': password}

    # setup our header info, which gives reddit a brief description of our app
    headers = {'User-Agent': user_agent}

    # send our request for an OAuth token
    res = requests.post('https://www.reddit.com/api/v1/access_token',
                        auth=auth, data=data, headers=headers)

    # convert response to JSON and pull access_token value
    TOKEN = res.json()['access_token']

    # add authorization to our headers dictionary
    headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}

    # while the token is valid (1 hr) we just add headers=headers to our requests
    requests.get('https://oauth.reddit.com/api/v1/me', headers=headers)

    return headers


def create_email(post_keys):
    message = MIMEMultipart()
    message["Subject"] = "GPU Found"
    message["From"] = sender_email
    message["To"] = receiver_email
    body = "<html><body>"

    # go through all posts and insert a link for each one
    for key in post_keys:
        post = most_recent_posts.get(key)
        print("New post found: {}".format(post['title']))
        body += "<p><a href=\"{}\"> {} </a><p>".format(post['url'], post['title'])

    body += "</body></html>"
    part = MIMEText(body, "html")
    message.attach(part)
    return message.as_string()


def compile_re(re_list):
    return re.compile('|'.join(re_list), flags=re.IGNORECASE)


if __name__ == '__main__':
    main()
