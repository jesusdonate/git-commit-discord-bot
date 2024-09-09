import os
from dotenv import load_dotenv
import json
import discord
from discord.ext import commands
import asyncio
from aiohttp import web

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

# Use environment variable for BOT_TOKEN
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Make sure DISCORD_CHANNEL_ID is an integer
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Create Flask app to listen to GitHub webhooks
app = web.Application()

async def github_webhook(request):
    print("Webhook received!")
    event_type = request.headers.get('X-GitHub-Event')
    print(f"GitHub Event Type: {event_type}")

    data = await request.json()
    print(f"Full webhook payload: {json.dumps(data, indent=2)}")

    if event_type == 'pull_request':
        if 'pull_request' in data:
            action = data['action']
            pull_request = data['pull_request']
            pr_title = pull_request['title']
            pr_url = pull_request['html_url']
            repository = data['repository']['full_name']

            message = f"**Pull Request {action}:** [{pr_title}]({pr_url}) in {repository}"
            print(f"Prepared message: {message}")

            # Send message to the Discord channel
            await send_message_to_discord(message)
        else:
            print("Event type is pull_request but no pull_request data found")
    elif event_type == 'push':
        if 'commits' in data:
            branch = data['ref'].split('/')[-1]
            commits = data['commits']
            pusher = data['pusher']['name']
            repository = data['repository']['full_name']
            compare_url = data['compare']

            commit_count = len(commits)
            commit_word = "commit" if commit_count == 1 else "commits"

            message = f"**New Push to {branch}:** {pusher} pushed {commit_count} {commit_word} to {repository}\n"
            message += f"[View changes]({compare_url})\n"

            # Add information about the commits (limit to 5 to avoid too long messages)
            for commit in commits[:5]:
                short_sha = commit['id'][:7]
                commit_message = commit['message'].split('\n')[0]  # Get only the first line
                message += f"- [`{short_sha}`] {commit_message}\n"

            if len(commits) > 5:
                message += f"... and {len(commits) - 5} more commits\n"

            print(f"Prepared message: {message}")

            # Send message to the Discord channel
            await send_message_to_discord(message)
        else:
            print("Event type is push but no commits data found")
    else:
        print(f"Received event type: {event_type}, not processing")

    return web.Response(text="Webhook received!")

# Send a message to the Discord channel
async def send_message_to_discord(message):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        try:
            await channel.send(message)
            print(f"Message sent to Discord: {message}")
        except Exception as e:
            print(f"Error sending message to Discord: {e}")
    else:
        print(f"Could not find channel with ID {DISCORD_CHANNEL_ID}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send("Hello, I'm online and ready to receive GitHub webhooks!")

async def start_aiohttp():
    app.add_routes([web.post('/github-webhook', github_webhook)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 3000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"AIOHTTP server started on http://0.0.0.0:{port}")

async def start_discord():
    await bot.start(BOT_TOKEN)

async def main():
    await asyncio.gather(
        start_aiohttp(),
        start_discord()
    )

if __name__ == "__main__":
    asyncio.run(main())
