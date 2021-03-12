# gpu-scraper
Automatically scrapes Reddit for GPUs for sale and sends an email/slack message if any are found. I wrote this to notify me ASAP when a GPU is posted on r/hardwareswap so that I can buy it for my mining rig.

At first I just queried Reddit and did a normal search with the names of GPUs I wanted, but that missed out on a lot of stuff.
I switched to using a very large search to return all results and then used regex to filter out the posts I want.
This way I get more accurate search results and can use the regex matches to automatically message users that seem to have exactly what I want to snipe the GPU as quickly as possible

The problem that I discovered is that notification time is limited by how long it takes for Reddit to index the search, which can be up to 2 minutes when Reddit is being slow. Now I directly query all of the newest posts in a subreddit and then use another layer of regex filtering to filter out posts that are only selling. This has resulted in a huge improvement in the time it takes for a notification to be sent, going from 1-2 minutes after post-time, to consistently at or below 15 seconds (!!!). 

## Features
- Search Reddit as fast as 60 times per minute (rate limit)
- Notifies in <15 seconds after someone makes a post
- Notify by email
- Notify by Slack message (instant)
- Automatically message users based on a fine regex filter WIP (subject to rate limit) 
