import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
import pandas
import requests
from dotenv import load_dotenv


def send_email(message, receiver_email):
    port = 465  # For gmail SSL
    email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(email, password)
        server.sendmail(email, receiver_email, message)


def create_email(sender, receiver, subject, link):
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = receiver

    # Create the plain-text and HTML version of your message
    html = """\
    <html>
      <body>
        <p>
           <a href=\"""" + link + "\">" + link + """</a>
        </p>
      </body>
    </html>
    """


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
    print(posts.head())
    return posts


"""
loop = Timeloop()
@loop.job(interval=timedelta(minutes=5))
def update_search():
    res = search_reddit(subreddit, search_string)
    global updated_posts
    updated_posts = parse_search(res)
"""

global prev_posts
global updated_posts
if __name__ == '__main__':
    # load secrets from .env file
    load_dotenv()
    # auth not needed for search
    # headers = authenticate_reddit()
    search_string = "(RX 470) OR (R9 390)"
    subreddit = "hardwareswap"

    res = search_reddit(subreddit, search_string)
    matching_posts = parse_search(res)
    # store results in a global var so the scheduled job can reference them
    global prev_posts
    prev_posts = matching_posts

    """
    # refresh the auth token before it expires
    @loop.job(interval=timedelta(minutes=50))
    def refresh_token():
        global headers
        headers = authenticate_reddit()
"""
