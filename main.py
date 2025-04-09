import discord
import feedparser
import os
from dotenv import load_dotenv
import yaml
import asyncio
import openai

load_dotenv()
intents = discord.Intents.all()
client = discord.Client(intents=intents)

DISCORD_CHANNEL_IDS = list(map(int, os.getenv('DISCORD_CHANNEL_IDS').split(',')))
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
RSS_FEED_URLS = os.getenv('RSS_FEED_URLS').split(",")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
EMOJI = "\U0001F4F0"
sent_articles_file = "sent_articles.yaml"

openai.api_key = OPENAI_API_KEY

async def summarize_article(article_content):
    try:
        response = await openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": f"다음 게시물 내용을 한국어로 요약해서 오직 결과값만 출력해줘: {article_content}"}
            ]
        )
        summary = response['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"Error summarizing article: {e}")
        return None

async def fetch_feed(channel):
    if os.path.exists(sent_articles_file):
        with open(sent_articles_file, "r") as f:
            sent_articles = yaml.safe_load(f)
        print("Loaded YAML object")
    else:
        sent_articles = {}
        print("Created new empty dictionary")

    for rss_feed_url in RSS_FEED_URLS:
        print("Parsing RSS feed...")
        feed = feedparser.parse(rss_feed_url)

        if feed.bozo:
            print(f"Error parsing RSS feed: {feed.bozo_exception}")
            continue

        last_entry = feed.entries[0]
        if channel.id not in sent_articles:
            sent_articles[channel.id] = []
        if last_entry.link not in sent_articles[channel.id]:
            article_title = last_entry.title
            article_link = last_entry.link
            article_content = last_entry.summary if 'summary' in last_entry else last_entry.description

            sent_articles[channel.id].append(last_entry.link)

            print(f"New article: {article_title}")
            print(f"Link: {article_link}")

            summary = await summarize_article(article_content)

            if summary:
                try:
                    await channel.send(f"{EMOJI}  |  {article_title}\n\nGPT 요약: {summary}\n\n{article_link}")
                    print("Article sent to channel successfully")
                except discord.Forbidden:
                    print("Error: Insufficient permissions to send messages to the channel")
                except discord.HTTPException as e:
                    print(f"Error sending message to the channel: {e}")

        print(f"Parsing complete for {rss_feed_url}")

    while True:
        try:
            with open(sent_articles_file, "w") as f:
                yaml.dump(sent_articles, f, default_flow_style=False, sort_keys=False)
            break
        except Exception as e:
            print(f"Error writing seen IDs to file: {e}")
            await asyncio.sleep(1)
    
@client.event
async def on_ready():
    print(f"Bot logged in as {client.user.name}")

    while True:
        for channel_id in DISCORD_CHANNEL_IDS:
            channel = client.get_channel(channel_id)
            print(f"Target channel: {channel.name} (ID: {channel.id})")
            await fetch_feed(channel)

        await asyncio.sleep(600)

print("Starting the bot...")
client.run(DISCORD_BOT_TOKEN)