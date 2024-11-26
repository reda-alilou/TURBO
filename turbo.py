import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp
import random
import datetime
import re
import json
import html

# Load the environment variables from the .env file
load_dotenv()
TOKEN = os.getenv("TURBO_TOKEN") # Load environment variables for secure access to sensitive data such as API keys and tokens.

# Load levels data
def load_levels_data():
    try:
        with open("levels.json", "r") as file: # Load levels.json to track user activity data for the leveling system.
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save levels data
def save_levels_data():
    with open("levels.json", "w") as file:
        json.dump(user_data, file, indent=4)

# Initialize levels data
user_data = load_levels_data()

def calculate_level(points):
    """Calculate the user's level based on their points."""
    return int(points ** 0.5)  # Level increases with square root of points

# Enable intents
intents = discord.Intents.default()
intents.message_content = True  # Enable reading message content
intents.members = True  # Required for member events (join, leave, update)
intents.guilds = True  # Required for guild-level events (bans, unbans, etc.)

# Create the bot with the intents
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) # # Initialize the bot with the "!" prefix for commands. Custom help command will be implemented later, so set to None.

# Forbidden words list
FORBIDDEN_WORDS = {"7mar", "kelb", "bghel"}  # Add your forbidden words here

# Allowed domains
ALLOWED_DOMAINS = {"youtube.com", "discord.com"}  # Add domains you want to allow

@bot.event
async def on_ready(): # Triggered when the bot is connected and ready to interact with Discord servers.
    print(f"Logged in as {bot.user.name} - {bot.user.id}") 
    print("Ready to go!")

@bot.event
async def on_member_join(member): # Triggered when a new member joins the server.
    # Sends a welcome message in the "👋welcome" channel and assigns the default "Member" role.
    channel = discord.utils.get(member.guild.text_channels, name="👋welcome")
    if channel:
        await channel.send(f"Welcome to the server, {member.mention}! We're glad to have you here. 🎉")
    
    # Assign the "Member" role to the new user
    role = discord.utils.get(member.guild.roles, name="Member")  # Find the role by name
    if role:
        await member.add_roles(role)
        print(f"Assigned {role.name} role to {member.name}") # Log the assignment of the role.
    else:
        print("Role not found!") # Log if the role is not found.    

# event to check messages for forbidden words and links and manage quiz answers and leveling system
@bot.event
async def on_message(message):
    """
    Handles message events: processes commands, filters forbidden words and links, and manages quiz answers.
    """
    global quiz_active, current_question, quiz_scores

    # Ignore messages from bots
    if message.author.bot:
        return

    # Check for forbidden words
    if any(word in message.content.lower() for word in FORBIDDEN_WORDS): 
        await message.delete()
        log_channel = discord.utils.get(message.guild.text_channels, name="📬logs") 
        if log_channel:
            await log_channel.send(
                f"🚨 A message from {message.author.mention} was deleted for containing forbidden words."
            )
        return  # Stop further processing of the message

    # Check for unauthorized links
    if "http" in message.content.lower():  # Rough check for links
        if not any(domain in message.content.lower() for domain in ALLOWED_DOMAINS):
            await message.delete() # Delete the message if it contains unauthorized links
            log_channel = discord.utils.get(message.guild.text_channels, name="📬logs") 
            if log_channel:
                await log_channel.send(
                    f"🚨 A message from {message.author.mention} was deleted for containing unauthorized links."
                )
            return  # Stop further processing of the message

    # Leveling system
    user_id = str(message.author.id)

    # Initialize user data if not present
    if user_id not in user_data:
        user_data[user_id] = {"points": 0, "level": 0}

    # Award points for the message
    user_data[user_id]["points"] += 1
    current_points = user_data[user_id]["points"]
    current_level = user_data[user_id]["level"]

    # Check for level-up
    new_level = calculate_level(current_points) # Calculate the new level based on the points
    if new_level > current_level: # Check if the user has leveled up
        user_data[user_id]["level"] = new_level # Update the user's level
        await notify_level_up(message.author, new_level, message.guild) # Notify the user about the level-up

    # Save updated data
    save_levels_data()

    # Quiz-related message processing
    if quiz_active and current_question:
        # Ensure the message is in the quiz channel and not a command
        if message.channel.name == quiz_channel_name and not message.content.startswith(bot.command_prefix):
            # Extract the user's answer
            user_answer = message.content.strip().lower()

            # Match the answer with the correct one
            if user_answer == current_question["answer"]:
                # Update the user's score
                if user_id not in quiz_scores:
                    quiz_scores[user_id] = 0
                quiz_scores[user_id] += 1

                # Notify the user and send the next question
                await message.channel.send(f"✅ **Correct!** Well done, {message.author.mention}. 🎉 You earned 1 point!")
                current_question = None
                await send_next_question(message.channel) # Send the next question
            elif user_answer.isdigit():
                # Handle numerical input for multiple-choice questions
                option_index = int(user_answer) - 1 # Convert the user's answer to an integer
                if 0 <= option_index < len(current_question["options"]): # Check if the option is valid
                    selected_option = current_question["options"][option_index] # Get the selected option
                    if selected_option == current_question["answer"]: # Check if the selected option is correct
                        # Update the user's score
                        if user_id not in quiz_scores: # Check if the user is in the quiz scores
                            quiz_scores[user_id] = 0 # Initialize the user's score
                        quiz_scores[user_id] += 1 # Increment the user's score

                        # Notify the user and send the next question
                        await message.channel.send(f"✅ **Correct!** Well done, {message.author.mention}. 🎉 You earned 1 point!")
                        current_question = None
                        await send_next_question(message.channel)
                    else:
                        await message.channel.send(f"❌ Wrong answer, {message.author.mention}. Try again!") # Notify the user about the incorrect answer
                else:
                    await message.channel.send(f"⚠️ Invalid option, {message.author.mention}. Please choose a valid number.") # Notify the user about the invalid option
            else:
                # Notify incorrect answers
                await message.channel.send(f"❌ Wrong answer, {message.author.mention}. Try again!")

    # Allow other commands to be processed
    await bot.process_commands(message) 

async def notify_level_up(user, new_level, guild):
    # Notifies the user in both the level-up channel and DMs. If DMs are disabled, logs an error message.
    level_up_message = f"🎉 {user.mention}, you have leveled up to **Level {new_level}!** 🌟"

    # Notify in the dedicated level-up channel
    level_up_channel = discord.utils.get(guild.text_channels, name="📈level")
    if level_up_channel:
        await level_up_channel.send(level_up_message)

    # Send private message to the user
    try:
        await user.send(f"🚀 Congratulations! You've reached **Level {new_level}** in {guild.name}! Keep it up! 🌟")
    except discord.Forbidden:
        print(f"Could not send level-up DM to {user.name}. They might have DMs disabled.")

# Event to check for forbidden words and links in edited messages
@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return  # Ignore bot messages
    
    # Detect forbidden words
    if any(word in after.content.lower() for word in FORBIDDEN_WORDS):
        await after.delete()
        log_channel = discord.utils.get(after.guild.text_channels, name="📬logs")
        if log_channel:
            await log_channel.send(
                f"🚨 A message from {after.author.mention} was deleted for containing forbidden words."
            )
        return  # Stop further processing of the message
    
    # check for forbidden links in edited messages
    if "http" in after.content.lower():  # Rough check for links
        if not any(domain in after.content.lower() for domain in ALLOWED_DOMAINS):
            await after.delete()
            log_channel = discord.utils.get(after.guild.text_channels, name="📬logs")
            if log_channel:
                await log_channel.send(
                    f"🚨 A message from {after.author.mention} was deleted for containing unauthorized links."
                )
            return  # Stop further processing of the message
    
    await bot.process_commands(after)  # Allow other commands to be processed

# Event to assign roles based on reactions
@bot.event
async def on_raw_reaction_add(payload):
    """ Triggered when a user reacts to a message.
        Assigns roles to users based on the emoji used. Uses the `reaction_roles` mapping. """
    if payload.member.bot:
        return  # Ignore bot reactions

    guild = bot.get_guild(payload.guild_id)
    role_name = None

    # Check which reaction triggered the event
    for category, emoji_map in reaction_roles.items():
        if str(payload.emoji) in emoji_map:
            role_name = emoji_map[str(payload.emoji)]
            break

    if role_name:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await payload.member.add_roles(role)
            print(f"Assigned role '{role_name}' to {payload.member.name}")

# Event to remove roles based on reactions
@bot.event
async def on_raw_reaction_remove(payload):
    """Remove role when a reaction is removed."""
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    if not member or member.bot:
        return  # Ignore bot reactions or invalid member

    role_name = None

    # Check which reaction triggered the event
    for category, emoji_map in reaction_roles.items():
        if str(payload.emoji) in emoji_map:
            role_name = emoji_map[str(payload.emoji)]
            break

    if role_name:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.remove_roles(role)
            print(f"Removed role '{role_name}' from {member.name}")

# Logging Events for Manual Actions
@bot.event
async def on_member_ban(guild, user):
    """Logs when a member is banned."""
    log_channel = discord.utils.get(guild.text_channels, name="📬logs")
    if log_channel:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            moderator = entry.user
            reason = entry.reason or "No reason provided."
            await log_channel.send(
                f"🚨 **BAN**: {user} was banned by {moderator}. Reason: {reason}"
            )

@bot.event
async def on_member_unban(guild, user):
    """Logs when a member is unbanned."""
    log_channel = discord.utils.get(guild.text_channels, name="📬logs")
    if log_channel:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            moderator = entry.user
            await log_channel.send(
                f"✅ **UNBAN**: {user} was unbanned by {moderator}."
            )

@bot.event
async def on_member_update(before, after):
    """Logs timeouts or other significant updates to a member."""
    log_channel = discord.utils.get(before.guild.text_channels, name="📬logs")
    if not log_channel:
        return

    # Check for timeout updates
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:  # Member was timed out
            timeout_expiry = after.timed_out_until.strftime("%Y-%m-%d %H:%M:%S UTC")
            await log_channel.send(
                f"⏱️ **TIMEOUT**: {after} was timed out until {timeout_expiry}."
            )
        else:  # Timeout was removed
            await log_channel.send(f"✅ **TIMEOUT REMOVED**: {after}'s timeout was lifted.")

@bot.event
async def on_member_remove(member):
    """Logs when a member is kicked."""
    log_channel = discord.utils.get(member.guild.text_channels, name="📬logs")
    if log_channel:
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target == member and entry.created_at > discord.utils.utcnow() - datetime.timedelta(seconds=10):
                moderator = entry.user
                reason = entry.reason or "No reason provided."
                await log_channel.send(f"🚨 **KICK**: {member} was kicked by {moderator}. Reason: {reason}")
                break

# error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the necessary permissions to run this command. 🚫")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide all required arguments for the command. 🤔")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please provide valid arguments for the command. 🤔")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try `!help` to see the available commands. 🤔")
    else:
        await ctx.send("An error occurred while running the command. 😢")

# Moderation Commands
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """ Bans a member from the server. Requires the 'ban_members' permission.
    - `ctx`: The context of the command, including the invoking user and channel.
    - `reason`: Optional reason for the ban, logged for moderation purposes.v"""
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} has been banned. 🚫")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kicks a member"""
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} has been kicked. 👢")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User, *, reason=None):
    """Unbans a user"""
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f"{user.mention} has been unbanned. ✅")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: str, *, reason=None):
    """Timeout a member for a specified duration."""
    match = re.match(r"(\d+)([smhd])", duration)  # Parse durations like "10m", "5h", "2d"
    if not match:
        await ctx.send("⛔ Invalid duration format. Use something like `10m` (minutes), `2h` (hours).")
        return

    amount, unit = int(match[1]), match[2]
    delta = {"s": datetime.timedelta(seconds=amount),
             "m": datetime.timedelta(minutes=amount),
             "h": datetime.timedelta(hours=amount),
             "d": datetime.timedelta(days=amount)}.get(unit)

    if not delta:
        await ctx.send("⛔ Invalid duration unit. Use `s`, `m`, `h`, or `d`.")
        return

    # Calculate timeout expiration
    timeout_until = datetime.datetime.now(datetime.timezone.utc) + delta
    await member.edit(timed_out_until=timeout_until, reason=reason)

    # Notify the user
    timeout_expiry = timeout_until.strftime("%Y-%m-%d %H:%M:%S UTC")
    await ctx.send(f"{member.mention} has been timed out for {amount}{unit}. Timeout ends at {timeout_expiry}. ⏱️")

@bot.command()
async def hello(ctx):
    await ctx.send("Hello! TURBO is online and ready!")

@bot.command()
async def blague(ctx):
    """Fetches a random joke from the Official Joke API."""
    url = "https://official-joke-api.appspot.com/random_joke"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                joke = f"{data['setup']} - {data['punchline']}"
                await ctx.send(joke)
            else:
                await ctx.send("Désolé, je n'ai pas pu récupérer une blague pour le moment. 😢")

@bot.command()
async def meme(ctx):
    """Fetches a random meme from r/memes using Reddit's public JSON API."""
    url = "https://www.reddit.com/r/memes/random/.json"

    headers = {"User-Agent": "Mozilla/5.0"}  # Reddit requires a user-agent

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # Parse the Reddit JSON structure
                post = data[0]["data"]["children"][0]["data"]
                meme_title = post["title"]
                meme_url = post["url"]
                
                # Send an embedded message
                embed = discord.Embed(title=meme_title, color=discord.Color.random())
                embed.set_image(url=meme_url)
                embed.set_footer(text="Source: r/memes")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Désolé, je n'ai pas pu récupérer un meme pour le moment. 😢")

@bot.command()
async def action(ctx, *, action_type=None):
    """Simulates an action (e.g., dancing, laughing)."""
    actions = {
        "dance": "💃 TURBO is dancing to the rhythm!",
        "laugh": "😂 TURBO is laughing uncontrollably!",
        "sing": "🎤 TURBO is singing a beautiful melody!",
        "run": "🏃 TURBO is running at lightning speed!",
        "sleep": "😴 TURBO is taking a nap!"
    }

    if action_type is None:
        # If no action is specified, send a random action
        action_type = random.choice(list(actions.keys()))
        await ctx.send(actions[action_type])
    elif action_type.lower() in actions:
        # If a specific action is given, send the corresponding message
        await ctx.send(actions[action_type.lower()])
    else:
        # If the action is not recognized, send a list of valid actions
        valid_actions = ", ".join(actions.keys())
        await ctx.send(f"🤔 I don't know how to do that. Try one of these: {valid_actions}.")

# command to clear messages
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    # Deletes the specified number of messages plus the command message itself.
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Cleared {amount} messages. 🧹", delete_after=5)

# command to display user's points and level
@bot.command()
async def mon_niveau(ctx):
    """Display the user's points and level."""
    user_id = str(ctx.author.id)
    if user_id not in user_data:
        await ctx.send(f"{ctx.author.mention}, you have no points yet. Start chatting to earn points! 🌟")
        return

    points = user_data[user_id]["points"]
    level = user_data[user_id]["level"]
    await ctx.send(f"{ctx.author.mention}, you currently have **{points} points** and are at **Level {level}!** 🚀")

# command to display the leaderboard
@bot.command()
async def leaderboard(ctx):
    """Display the top users by points."""
    if not user_data:
        await ctx.send("No data available yet. Start chatting to earn points! 🌟")
        return

    # Sort users by points
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["points"], reverse=True)
    leaderboard_message = "**🏆 Leaderboard 🏆**\n"
    for i, (user_id, data) in enumerate(sorted_users[:10], start=1):  # Top 10 users
        try:
            user = await bot.fetch_user(int(user_id))
            leaderboard_message += f"{i}. {user.name}: {data['points']} points (Level {data['level']})\n"
        except discord.NotFound:
            leaderboard_message += f"{i}. [Unknown User]: {data['points']} points (Level {data['level']})\n"

    await ctx.send(leaderboard_message)

# quiz categories command
@bot.command()
async def quiz_categories(ctx):
    """Displays a list of quiz categories and their corresponding IDs."""
    categories = {
        9: "General Knowledge",
        10: "Books",
        11: "Film",
        12: "Music",
        13: "Musicals & Theatres",
        14: "Television",
        15: "Video Games",
        16: "Board Games",
        17: "Science & Nature",
        18: "Computers",
        19: "Mathematics",
        20: "Mythology",
        21: "Sports",
        22: "Geography",
        23: "History",
        24: "Politics",
        25: "Art",
        26: "Celebrities",
        27: "Animals",
        28: "Vehicles",
        29: "Comics",
        30: "Gadgets",
        31: "Anime & Manga",
        32: "Cartoons & Animations"
    }
    category_list = "\n".join([f"**{category_id}:** {name}" for category_id, name in categories.items()])
    await ctx.send(f"**Available Quiz Categories**\n{category_list}")

# help command
@bot.command()
async def help(ctx):
    """Displays the list of available commands."""
    help_message = """
**Available Commands**

**General:**
- `!hello`: Displays a welcome message.
- `!blague`: Fetches a random joke.
- `!meme`: Fetches a random meme.
- `!action [action]`: Simulates an action (e.g., dance, laugh).

**services:**
- `!weather [city]`: Fetches the current weather for a city.

**Moderation:**
- `!ban [member] [reason]`: Bans a member.
- `!kick [member] [reason]`: Kicks a member.
- `!unban [user] [reason]`: Unbans a user.
- `!timeout [member] [duration] [reason]`: Times out a member for a specified duration.
- `!clear [amount]`: Clears a specified number of messages.

**Reaction Roles:**
- `!setup_roles`: Sets up reaction role messages in the roles channel.

**Levels:**
- `!mon_niveau`: Displays your current points and level.
- `!leaderboard`: Displays the top users by points.

**Quiz:**
- `!start_quiz [category] [difficulty]`: Starts a quiz with optional arguments:
  - **Category (optional)**: Specify a category ID. Use `!quiz_categories` to view available categories.
  - **Difficulty (optional)**: Specify 'easy', 'medium', or 'hard'.
  - Example: `!start_quiz 18 medium`
- `!end_quiz`: Ends the current quiz.
- `!quiz_categories`: Displays a list of quiz categories and their IDs.

**Miscellaneous:**
- `!help`: Displays this help message.

Use each command with the specified arguments if needed! 🚀
"""
    await ctx.send(help_message)

# Reaction-role mapping
reaction_roles = {
    "gender": {
        "🎀": "female",
        "👨🏻": "male"
    },
    "age": {
        "🔞": "18-21",
        "🎓": "22-24",
        "💼": "25-29",
        "🎂": "30+"
    },
    "continent": {
        "🌍": "africa",
        "🌏": "asia",
        "🇪🇺": "europe",
        "🇺🇸": "north america",
        "🇧🇷": "south america",
        "🌊": "oceania"
    },
    "dm_status": {
        "💌": "DMs open",
        "⚠️": "DMs ask",
        "🚫": "DMs closed"
    },
    "color": {
        "💚": "green",
        "💛": "yellow",
        "💙": "blue",
        "❤️": "red",
        "💜": "purple",
        "🧡": "orange"
    }
}

# Command to set up reaction roles
@bot.command()
@commands.has_permissions(manage_roles=True)
async def setup_roles(ctx):
    """Set up reaction role messages in the roles channel."""
    roles_channel = discord.utils.get(ctx.guild.text_channels, name="⭕roles")
    if not roles_channel:
        await ctx.send("Roles channel not found!")
        return

    # Gender Roles Embed
    gender_embed = discord.Embed(
        title="Gender",
        description="\n".join(
            [f"{emoji}: `{role.capitalize()}`" for emoji, role in reaction_roles["gender"].items()]
        ),
        color=discord.Color.blurple()
    )
    gender_embed.set_footer(text="React to get your gender role.")
    gender_message = await roles_channel.send(embed=gender_embed)
    for emoji in reaction_roles["gender"]:
        await gender_message.add_reaction(emoji)

    # Age Roles Embed
    age_embed = discord.Embed(
        title="Age",
        description="\n".join(
            [f"{emoji}: `{role}`" for emoji, role in reaction_roles["age"].items()]
        ),
        color=discord.Color.green()
    )
    age_embed.set_footer(text="React to get your age group role.")
    age_message = await roles_channel.send(embed=age_embed)
    for emoji in reaction_roles["age"]:
        await age_message.add_reaction(emoji)

    # Continent Roles Embed
    continent_embed = discord.Embed(
        title="Continent",
        description="\n".join(
            [f"{emoji}: `{role.replace('_', ' ').capitalize()}`" for emoji, role in reaction_roles["continent"].items()]
        ),
        color=discord.Color.gold()
    )
    continent_embed.set_footer(text="React to get your continent role.")
    continent_message = await roles_channel.send(embed=continent_embed)
    for emoji in reaction_roles["continent"]:
        await continent_message.add_reaction(emoji)

    # DM Status Roles Embed
    dm_status_embed = discord.Embed(
        title="DM Status",
        description="\n".join(
            [f"{emoji}: `{role}`" for emoji, role in reaction_roles["dm_status"].items()]
        ),
        color=discord.Color.purple()
    )
    dm_status_embed.set_footer(text="React to set your DM status.")
    dm_status_message = await roles_channel.send(embed=dm_status_embed)
    for emoji in reaction_roles["dm_status"]:
        await dm_status_message.add_reaction(emoji)

    # Color Roles Embed
    color_embed = discord.Embed(
        title="Color",
        description="\n".join(
            [f"{emoji}: `{role}`" for emoji, role in reaction_roles["color"].items()]
        ),
        color=discord.Color.teal()
    )
    color_embed.set_footer(text="React to set your display color.")
    color_message = await roles_channel.send(embed=color_embed)
    for emoji in reaction_roles["color"]:
        await color_message.add_reaction(emoji)

    await ctx.send("Reaction roles setup complete!")

# Global variables to manage quiz state
quiz_active = False
quiz_channel_name = "🤔quiz"
quiz_scores = {}
quiz_questions = []  # Placeholder for questions (to be loaded or fetched later)
current_question = None

# Command to start the quiz
@bot.command()
@commands.has_permissions(manage_guild=True)
async def start_quiz(ctx, category: int = None, difficulty: str = None):
    # Fetches questions from the Open Trivia Database API. If no category or difficulty is provided, defaults are used.
    global quiz_active, quiz_scores, quiz_questions, current_question

    # Ensure the command is run in the designated quiz channel
    if ctx.channel.name != quiz_channel_name:
        await ctx.send(f"⚠️ This command can only be used in the `{quiz_channel_name}` channel.")
        return

    # Prevent multiple quizzes from running simultaneously
    if quiz_active:
        await ctx.send("🚨 A quiz is already running! Use `!end_quiz` to stop the current quiz.")
        return

    # Initialize the quiz
    quiz_active = True
    quiz_scores = {}
    quiz_questions = []

    # Base API URL for Open Trivia Database
    api_url = "https://opentdb.com/api.php?amount=5"
    
    # Add category and difficulty filters if provided
    if category:
        api_url += f"&category={category}"
    if difficulty:
        api_url += f"&difficulty={difficulty.lower()}"
    
    # Fetch questions from the API
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                if data["response_code"] == 0:  # Successful response
                    for item in data["results"]:
                        question = {
                            "question": html.unescape(item["question"]),  # Decode question text
                            "answer": html.unescape(item["correct_answer"]).lower(),  # Decode and lowercase correct answer
                            "options": [html.unescape(ans).lower() for ans in item["incorrect_answers"]] + [html.unescape(item["correct_answer"]).lower()]
                        }
                        random.shuffle(question["options"])  # Shuffle options for variety
                        quiz_questions.append(question)
                else:
                    await ctx.send("⚠️ Failed to fetch quiz questions. Please try again later.")
                    quiz_active = False
                    return
            else:
                await ctx.send("⚠️ Unable to connect to the trivia API. Please try again later.")
                quiz_active = False
                return

    current_question = None
    await ctx.send("🎉 **Quiz started!** Mods or Admins can end it using `!end_quiz`. Get ready!")
    await send_next_question(ctx)

async def send_next_question(ctx):
    # Sends the next question in the quiz. If no questions remain, announces the end of the quiz.
    global quiz_questions, current_question

    if not quiz_questions:
        await ctx.send("🎉 **Quiz finished!** No more questions available.")
        return

    current_question = quiz_questions.pop(0)
    options = "\n".join([f"{i+1}. {option}" for i, option in enumerate(current_question["options"])])
    await ctx.send(f"❓ **Question:** {current_question['question']}\n\n{options}")

# Command to end the quiz
@bot.command()
@commands.has_permissions(manage_guild=True)
async def end_quiz(ctx):
    global quiz_active, quiz_scores

    # Ensure the command is run in the designated quiz channel
    if ctx.channel.name != quiz_channel_name:
        await ctx.send(f"⚠️ This command can only be used in the `{quiz_channel_name}` channel.")
        return

    # Check if a quiz is active
    if not quiz_active:
        await ctx.send("⚠️ No quiz is currently running!")
        return

    quiz_active = False
    await ctx.send("🚨 **Quiz ended!** Here are the final scores:")

    # Display final scores
    if quiz_scores:
        leaderboard = sorted(quiz_scores.items(), key=lambda x: x[1], reverse=True)
        score_message = "\n".join([f"**{i+1}. {bot.get_user(int(user)).name}** - {score} points"
                                   for i, (user, score) in enumerate(leaderboard)])
        await ctx.send(f"🏆 **Final Leaderboard** 🏆\n{score_message}")
    else:
        await ctx.send("No one participated in the quiz. 😢")

# Command to fetch the current weather
@bot.command()
async def weather(ctx, *, city: str):
    """
    Fetches the current weather for the specified city.
    Usage: !weather [city]
    Example: !weather London
    """
    # OpenWeather API configuration
    api_key = os.getenv("OPENWEATHER_API_KEY")
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    # Construct API URL
    params = {"q": city, "appid": api_key, "units": "metric"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # Extract weather data
                city_name = data["name"]
                weather_description = data["weather"][0]["description"].capitalize()
                temperature = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                
                # Create and send an embedded message
                embed = discord.Embed(
                    title=f"Weather in {city_name}",
                    description=f"{weather_description}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Temperature", value=f"{temperature}°C", inline=True)
                embed.add_field(name="Feels Like", value=f"{feels_like}°C", inline=True)
                embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
                embed.set_footer(text="Data provided by OpenWeather")
                
                await ctx.send(embed=embed)
            elif response.status == 404:
                await ctx.send("City not found. Please check the spelling and try again. 🌍")
            else:
                await ctx.send("Sorry, I couldn't fetch the weather data right now. Please try again later. 😢")

# Run the bot
bot.run(TOKEN)
