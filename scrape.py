import os
import smtplib
import ssl
from datetime import timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import regex as re
from slack_sdk.webhook import WebhookClient
import requests
from dotenv import load_dotenv
from timeloop import Timeloop
from SlidingWindowMap import SlidingWindowMap

# load secrets from .env file
load_dotenv()

sender_email = os.getenv("EMAIL_ADDRESS")
sender_password = os.getenv("EMAIL_PASSWORD")
receiver_email = os.getenv("RECEIVE_EMAIL")
user_agent = os.getenv("USER_AGENT")
slack_url = os.getenv("SLACK_WEB_HOOK_URL")
print("Sending from: " + sender_email)
print("Receiving at: " + receiver_email)
print("UserAgent: " + user_agent)

# used for notifications (manual handling)
coarse_regex = [
    r"(?<!\$)(1[0-5][0-9]{2})(?!p|0)(?:[\s-]*?(watt|w)|[\s\S]*?(power supply|psu)+)",  # match posts with 1000w+ psus
    r"(?<!\$)(1(?:0[67]|66)0)(?=[\s\S]*?(?:gpu|graphic))",  # match posts with nvidia series followed by "gpu"/"graphic"
    r"(RX\s?[45][78]0)|(?<!\$)([45][78]0)(?!\d+|[\s-]*(usd|dollar))(?=[\s\S]*?(?:gpu|graphic))"
    # match posts with amd series that arent prices and gpus
]
# used for automated replies to posts
fine_regex = [
    r"(?(?<=gtx)\s*(1(?:0[67]|66)0)|(1(?:0[67]|66)0)(?:[\s-]*)(6gb?))",  # match permutations of gtx 1060 6gb
    r"(?<=\[H\]).*(1(?:0[67]|66)0)(?=.*\[W\])",  # match nvidia series in title with "have"
    r"(RX\s?[45][78]0)(?:[\s-]*)(8gb?)",  # match permutations of rx470 8gb
    r"(?<=\[H\]).*([45][78]0)(?=.*\[W\])"
]
search_string = "USA"
# search_string = "PSU OR (RX 470) OR (R9 390) OR (RX 570) OR (RX 480) OR (RX 580) OR (1060) OR (1660)"
subreddit = "hardwareswap"
post_update_interval_seconds = 5
search_result_limit = 30

job_loop = Timeloop()
most_recent_posts = SlidingWindowMap(search_result_limit)


def main():
    # auth not needed for search
    # headers = authenticate_reddit()

    # compile regexp for search
    global coarse_regex
    global fine_regex
    coarse_regex = compile_re(coarse_regex)
    fine_regex = compile_re(fine_regex)

    # start the job loop to continuously check for new posts
    job_loop.start(block=True)


@job_loop.job(interval=timedelta(seconds=post_update_interval_seconds))
def update_search():
    curr_time = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    print("[{}] Rerunning search...".format(curr_time))
    try:
        res = search_reddit(subreddit, search_string)
        updated_posts = parse_search(res)
    except AssertionError as e:
        print("Error searching reddit: {}".format(e))

    # only save keys for the post and use the most_recent map to get the actual post
    # to save time/space
    new_post_keys = set()
    for post in updated_posts:
        # if the key was successfully added we know it "pushed" another one out of its spot
        # therefore its a new post
        title = post['title']
        if most_recent_posts.put(title, post):
            new_post_keys.add(title)

    # filter out the posts we want using regex
    coarse_keys = regex_filter(new_post_keys, coarse_regex)
    get_title = lambda posts: "{} new posts found".format(len(posts))
    if coarse_keys:
        notify(coarse_keys, "COARSE - {}".format(get_title(coarse_keys)))
        fine_keys = regex_filter(coarse_keys, fine_regex)
        if fine_keys:
            notify(fine_keys, "FINE - {}".format(get_title(fine_keys)))
    else:
        print("No new posts found")


def notify(post_keys, title):
    # send a slack message/email if there are new posts
    print("{} new posts found".format(len(post_keys)))
    # email_message = create_email(new_posts)
    # send the notification
    try:
        notify_slack(post_keys, title)
        print("Slack message sent to: {}".format(slack_url))

        # send_email(email_message)
        # print("Email sent to: {} from: {}".format(receiver_email, sender_email))
    except AssertionError as e:
        print("Error sending notification: {}".format(e))

    """
    # refresh the auth token before it expires
    @loop.job(interval=timedelta(minutes=50))
    def refresh_token():
        global headers
        headers = authenticate_reddit()
"""


def notify_slack(post_keys, title):
    webhook = WebhookClient(slack_url)
    curr_time = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    # make a list of the new posts in markdown
    text = "[{}] {}\n".format(curr_time, title) \
           + "\n".join(["*<{}|{}>*"
                       .format(most_recent_posts.get(k)['url'],
                               most_recent_posts.get(k)['title'])
                        for k in post_keys])
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

    assert response.status_code == 200, "{} received from Slack".format(response.status_code)
    assert response.body == "ok", "{} received from Slack".format(response.body)


def search_reddit(subreddit, search_string):
    # query newest posts
    headers = {'User-Agent': user_agent}
    # small search result limit to reduce randomness of queries that return a large amount of results
    params = {'q': search_string, 'limit': str(search_result_limit), 'sort': 'new', 't': 'week', 'restrict_sr': 'true'}
    res = requests.get("https://reddit.com/r/{}/search.json".format(subreddit), params=params, headers=headers)
    assert res.status_code == 200, "{} received from reddit".format(res.status_code)
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
            'url': post['data']['url']
        }
        posts.append(data)

    # filter to only posts that are selling
    posts = filter(lambda data: data['flair'] == 'SELLING', posts)
    return posts


def regex_filter(post_keys, reg_exp):
    matching_posts_keys = set()
    for key in post_keys:
        post = most_recent_posts.get(key)
        matches = re.findall(reg_exp, post['title'] + post['body'])
        if len(matches) > 0:
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