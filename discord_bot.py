import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from agents.coordinator_agent import CoordinatorAgent
try:
    from agents.marketing_agent import MarketingAgent
except ImportError:
    MarketingAgent = None  # Handle the absence gracefully
from agents.finance_agent import FinanceAgent

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not DISCORD_BOT_TOKEN:
    sys.exit('ERROR: DISCORD_BOT_TOKEN is not set. Add it to your .env file.')

# Set up intents
from discord import Intents

intents = Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Instantiate agents
coordinator = CoordinatorAgent()
# marketing_agent = MarketingAgent()
finance_agent = FinanceAgent()
# admin_agent = AdministrativeAgent()

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}!')
    try:
        import agent_registry
        agent_registry.register("DiscordBot", f"Discord bot integration ({bot.user})")
    except Exception:
        pass

@bot.command()
async def test_input_expenses(ctx):
    await ctx.send("It's time to update your January expenses for Ivan Cartage. Please provide the amounts. Tolls:")

@bot.command()
async def input_expenses(ctx):
    print(f'Received command in channel: {ctx.channel.name}')  # Debugging log
    if ctx.channel.name == 'finance':
        print('Detected /input_expenses command')  # Check for finance channel
        await finance_agent.request_monthly_expenses(ctx)  # Call finance agent method
    else:
        await ctx.send('This command can only be used in the finance channel.')

@bot.event
async def on_message(message):
    print(f"Received message: {message.content}")  # Debug log
    await bot.process_commands(message)  # Ensure commands can still be processed

# Run the bot
bot.run(DISCORD_BOT_TOKEN)