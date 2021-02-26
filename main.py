import os
import smtplib
import ssl
from datetime import timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from slack_sdk.webhook import WebhookClient
import pandas
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

search_string = "(RX 470) OR (R9 390) OR (RX 570) OR (RTX 3070) OR (RX 480) OR (RX 580) OR (1060) OR (1660)"
subreddit = "hardwareswap"
post_update_interval_minutes = 2
search_result_limit = 10

job_loop = Timeloop()
most_recent_posts = SlidingWindowMap(search_result_limit)

def main():
    # auth not needed for search
    # headers = authenticate_reddit()
    global prev_posts
    res = search_reddit(subreddit, search_string)
    matching_posts = parse_search(res)
    # store results in a global var so the scheduled job can reference them
    prev_posts = matching_posts
    # start the job loop to continuously check for new posts
    job_loop.start(block=True)


@job_loop.job(interval=timedelta(minutes=post_update_interval_minutes))
def update_search():
    dt_string = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    print("[{}] Rerunning search...".format(dt_string))
    res = search_reddit(subreddit, search_string)
    updated_posts = parse_search(res)

    new_posts = []
    for i, post in updated_posts.iterrows():
        # if the key was successfully added we know it "pushed" another one out of its spot
        # therefore its a new post
        if most_recent_posts.put(post['title'], post):
            new_posts.append(post)

    """
    # take set difference to get the new posts
    # left join
    new_posts = updated_posts.merge(prev_posts, how='left', indicator=True)
    # take only rows unique to updated_posts
    new_posts = new_posts[new_posts['_merge'] == 'left_only']
    new_posts.drop(columns='_merge', inplace=True)
    """

    # send a slack message/email if there are new posts
    if len(new_posts) > 0:
        print("{} new posts found".format(len(new_posts)))
        # email_message = create_email(new_posts)
        # send the notification
        try:
            notify_slack(new_posts)
            print("Slack message sent to: {}".format(slack_url))

            #send_email(email_message)
            #print("Email sent to: {} from: {}".format(receiver_email, sender_email))
        except AssertionError as e:
            print("Error sending notification\n" + e)
    else:
        print("No new posts found")

    # update the previous posts to include the new ones we just found
    prev_posts = updated_posts.copy()

    """
    # refresh the auth token before it expires
    @loop.job(interval=timedelta(minutes=50))
    def refresh_token():
        global headers
        headers = authenticate_reddit()
"""


def search_reddit(subreddit, search_string):
    # query newest posts
    headers = {'User-Agent': user_agent}
    # small search result limit to reduce randomness of queries that return a large amount of results
    params = {'q': search_string, 'limit': str(search_result_limit), 'sort': 'new', 't': 'week', 'restrict_sr': 'true'}
    res = requests.get("https://reddit.com/r/{}/search.json".format(subreddit), params=params, headers=headers)
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
    # convert the list into a pandas dataframe - this is faster than appending dicts to a dataframe
    posts = pandas.DataFrame(posts)
    return posts


def notify_slack(posts):
    webhook = WebhookClient(slack_url)
    blocks = []
    # go through all posts and add a markdown section for each one
    for post in posts:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "GPU Found\n*<{}|{}>*".format(post['url'], post['title'])
                }
            })

    # send the slack message
    response = webhook.send(
        text="GPU Found",
        blocks=blocks
    )

    assert response.status_code == 200, "200 not received from Slack"
    assert response.body == "ok", "OK not received from Slack"


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


def create_email(posts):
    message = MIMEMultipart()
    message["Subject"] = "GPU Found"
    message["From"] = sender_email
    message["To"] = receiver_email
    body = "<html><body>"

    # go through all posts and insert a link for each one
    for post in posts:
        print("New post found: {}".format(post['title']))
        body += "<p><a href=\"{}\"> {} </a><p>".format(post['url'], post['title'])

    body += "</body></html>"
    part = MIMEText(body, "html")
    message.attach(part)
    return message.as_string()


if __name__ == '__main__':
    main()


