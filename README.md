# gpu-scraper
Automatically scrapes reddit for new posts in a search and sends an email/slack message if any are found. 
I wrote this to run 24/7 on my server to constantly scrape r/hardwareswap for GPUs so that I can buy them for my crypto mining server.

At first I just queried Reddit and did a normal search with the names of GPUs I wanted, but that missed out on a lot of stuff.
Now I do a very large search to return all results and then use regex to filter out the posts I want.
This way I get more accurate search results and can use the regex matches to automatically message users that seem to have exactly what I want to snipe the GPU as quickly as possible

## Features
- Search Reddit as fast as 60 times per minute (rate limit)
- Notify by email
- Notify by Slack message (instant)
- Automatically message users based on a fine regex filter
