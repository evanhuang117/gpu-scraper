import os
import smtplib
import ssl
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas
import requests
from dotenv import load_dotenv
from timeloop import Timeloop

# load secrets from .env file
load_dotenv()

sender_email = os.getenv("EMAIL_ADDRESS")
sender_password = os.getenv("EMAIL_PASSWORD")
receiver_email = os.getenv("RECEIVE_EMAIL")
search_string = "(RX 470) OR (R9 390)"
subreddit = "hardwareswap"
job_loop = Timeloop()
post_update_interval = timedelta(minutes=5)
prev_posts = pandas.DataFrame()


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


@job_loop.job(interval=post_update_interval)
def update_search():
    global prev_posts
    print("Rerunning search...")
    res = search_reddit(subreddit, search_string)
    updated_posts = parse_search(res)
    # take set difference to get the new posts
    new_posts = pandas.concat([prev_posts, updated_posts]).drop_duplicates(keep=False)

    # go through new posts and send an email with their links
    if new_posts.size > 0:
        email_message = create_email(new_posts)
        print(email_message)
        # send the email
        try:
            send_email(email_message)
            print("Email sent to: " + receiver_email + " from: " + sender_email)
        except:
            print("Error sending email")
    else:
        print("No new posts found")

    # update the previous posts to include the new ones we just found
    prev_posts = updated_posts

    """
    # refresh the auth token before it expires
    @loop.job(interval=timedelta(minutes=50))
    def refresh_token():
        global headers
        headers = authenticate_reddit()
"""

def search_reddit(subreddit, search_string):
    # query newest posts
    headers = {'User-Agent': 'EvansRedditGPUFinder/0.0.1'}
    params = {'q': search_string, 'limit': '100', 'sort': 'new', 't': 'month', 'restrict_sr': 'true'}
    res = requests.get("https://reddit.com/r/" + subreddit + "/search.json", params=params, headers=headers)
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
    headers = {'User-Agent': 'SearchReddit/0.0.1'}

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
    for i, post in posts.iterrows():
        print("New post found: " + post['title'])
        body += "<p><a href=\"" + post['url'] + "\">" + post['title'] + "</a><p>"

    body += "</body></html>"
    part = MIMEText(body, "html")
    message.attach(part)
    return message.as_string()


if __name__ == '__main__':
    main()


