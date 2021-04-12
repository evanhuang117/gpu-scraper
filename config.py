import os

from dotenv import load_dotenv

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

search_string = ""
subreddit = "hardwareswap"
post_update_interval_seconds = 5
search_result_limit = 30

# used for notifications (manual handling)
coarse_regex = [
    #   r"(?<!\$)(1[0-5][0-9]{2})(?!p|0)(?:[\s-]*?(watt|w)|[\s\S]*?(power supply|psu)+)",  # match posts with 1000w+ psus
    # r"(?<!\$)(1(?:0[678]|66)0)(?=[\s\S]*?(?:gpu|graphic))",
    r"(?<!\$)([23]0[789]0)(?=[\s\S]*?(?:gpu|graphic))",
    # match posts with nvidia series followed by "gpu"/"graphic"
    # r"GTX\s*(1(?:0[678]|66)0)",
    r"(RTX|GTX)\s*([23]0[789]0)",
    # match posts with amd series that arent prices and gpus
    r"(RX\s?[45][78]0)|(?<!\$)([45][78]0)(?!\d+|[\s-]*(usd|dollar))(?=[\s\S]*?(?:gpu|graphic))",
    # posts about r9 390 gpus
    r"R9[\s-]*390(?=[\s\S]*?(?:gpu|graphic))"
]
# used for automated replies to posts
fine_regex = [
    # match permutations of 1060 6gb in the title only
    # r"\[H\](?!.*(full pc|pre[\s-]*built|build)).*?((1(?:0[78]|66)0)(?!\s?p)|(1060)[\s-]*(6gb?))(?=.*\[W\])",
    r"\[H\](?!.*(full pc|pre[\s-]*built|build)).*?(RTX|GTX)\s*([23]0[789]0)(?=.*\[W\])",
    # r"(?<=\[H\]).*(1(?:0[67]|66)0)(?=.*\[W\])",  # match nvidia series in title with "have"
    # match permutations of 8gb AMD cards we want in the title only
    r"\[H\](?!.*(full pc|pre[\s-]*built|build)).*?(RX\s?[45][78]0)(?:[\s-]*)(8gb?)(?=.*\[W\])",
    # r"(?<=\[H\]).*([45][78]0)(?=.*\[W\])"
    # match r9 390s in the title
    r"\[H\](?!.*(full pc|pre[\s-]*built|build)).*?(R9[\s-]*390)(?=.*\[W\])"
]
price_regex = [
    r"(?P<gpu>(?:RTX|GTX)?\s*(?:[23]0[789]0))[\s\S]*?"
    r"(?P<price>(?P<s>\$)?(?(s)\d{1,3}(?:,?\d{3})*\b|\d{1,3}(?:,?\d{3})*\s*?(?:USD|dollars|shipped|OBO)))",

]
title_regex = [
    r"\[USA.*?\].*\[H\].*?\[W\].*(pay[\s-]*pal|\bPP)"  # filter out only posts that want paypal (selling)
]
