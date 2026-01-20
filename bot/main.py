"""
Ironbrew 2 Discord Bot
Lua Obfuscator Bot using Ironbrew 2
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from aiohttp import web

from obfuscator import obfuscate_lua

# ============================================
# Configuration
# ============================================
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('BOT_PREFIX', '!')
PORT = int(os.getenv('PORT', 10000))

# Validate token
if not TOKEN:
    print("=" * 50)
    print("ERROR: DISCORD_TOKEN environment variable not set!")
    print("Please set it in Render Dashboard -> Environment")
    print("=" * 50)
    exit(1)

# ============================================
# Bot Setup
# ============================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX, 
    intents=intents,
    help_command=None  # Disable default help
)

# ============================================
# Health Check Server (Required by Render)
# ============================================
async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', health_handler)
    app.router.add_get('/health', health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"[Health] Server running on port {PORT}")

# ============================================
# Slash Commands Definition
# ============================================
@bot.tree.command(name="obfuscate", description="Obfuscate a Lua file with Ironbrew 2")
@app_commands.describe(file="The .lua file to obfuscate")
async def slash_obfuscate(interaction: discord.Interaction, file: discord.Attachment):
    """Slash command untuk obfuscate file Lua"""
    
    # Validasi ekstensi
    if not file.filename.lower().endswith('.lua'):
        await interaction.response.send_message(
            "❌ Only `.lua` files are accepted!", 
            ephemeral=True
        )
        return
    
    # Validasi ukuran (max 2MB)
    if file.size > 2 * 1024 * 1024:
        await interaction.response.send_message(
            "❌ File too large! Maximum size is 2MB.", 
            ephemeral=True
        )
        return
    
    # Defer response (processing)
    await interaction.response.defer(thinking=True)
    
    try:
        # Download file
        lua_content = await file.read()
        lua_content = lua_content.decode('utf-8')
        
        # Obfuscate
        result, success, error_msg = await obfuscate_lua(lua_content, file.filename)
        
        if success:
            output_filename = f"obf_{file.filename}"
            discord_file = discord.File(fp=result, filename=output_filename)
            
            embed = discord.Embed(
                title="✅ Obfuscation Successful!",
                description="Your Lua script has been obfuscated with Ironbrew 2",
                color=discord.Color.green()
            )
            embed.add_field(name="📄 Input", value=f"`{file.filename}`", inline=True)
            embed.add_field(name="🔒 Output", value=f"`{output_filename}`", inline=True)
            embed.add_field(
                name="📊 Size",
                value=f"{file.size:,} → {result.getbuffer().nbytes:,} bytes",
                inline=True
            )
            embed.set_footer(text="Powered by Ironbrew 2")
            
            await interaction.followup.send(embed=embed, file=discord_file)
        else:
            embed = discord.Embed(
                title="❌ Obfuscation Failed",
                description=f"```\n{error_msg[:1500]}\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
    except UnicodeDecodeError:
        await interaction.followup.send("❌ Error: File is not valid UTF-8 encoded text!")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: `{latency}ms`")


@bot.tree.command(name="help", description="Show bot help and commands")
async def slash_help(interaction: discord.Interaction):
    """Show help embed"""
    embed = discord.Embed(
        title="🔒 Ironbrew 2 - Lua Obfuscator Bot",
        description="Obfuscate your Lua scripts using Ironbrew 2",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📝 Slash Commands",
        value="""
`/obfuscate` - Obfuscate a Lua file
`/ping` - Check bot latency
`/help` - Show this help
        """,
        inline=False
    )
    embed.add_field(
        name="📝 Prefix Commands",
        value=f"""
`{PREFIX}obfuscate` - Obfuscate (attach .lua file)
`{PREFIX}ping` - Check latency
`{PREFIX}help` - Show help
        """,
        inline=False
    )
    embed.add_field(
        name="📎 How to Use",
        value="1. Use `/obfuscate` command\n2. Attach your `.lua` file\n3. Wait for obfuscation\n4. Download the result!",
        inline=False
    )
    embed.add_field(
        name="⚠️ Limits",
        value="• Max file size: 2MB\n• File type: `.lua` only\n• Timeout: 2 minutes",
        inline=False
    )
    embed.set_footer(text="Ironbrew 2 | .NET 3.1 + Lua 5.1")
    
    await interaction.response.send_message(embed=embed)


# ============================================
# Prefix Commands
# ============================================
@bot.command(name='obfuscate', aliases=['obf', 'ib2', 'ironbrew'])
async def cmd_obfuscate(ctx):
    """Obfuscate Lua file dengan Ironbrew 2"""
    
    # Check attachment
    if not ctx.message.attachments:
        embed = discord.Embed(
            title="❌ No File Attached",
            description="Please attach a `.lua` file to obfuscate!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📝 Usage",
            value=f"1. Type `{PREFIX}obfuscate`\n2. Attach your `.lua` file",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    attachment = ctx.message.attachments[0]
    
    # Validate
    if not attachment.filename.lower().endswith('.lua'):
        await ctx.send("❌ Only `.lua` files are accepted!")
        return
    
    if attachment.size > 2 * 1024 * 1024:
        await ctx.send("❌ File too large! Maximum 2MB.")
        return
    
    # Processing embed
    processing_embed = discord.Embed(
        title="⏳ Processing...",
        description=f"Obfuscating `{attachment.filename}`\nPlease wait...",
        color=discord.Color.blue()
    )
    processing_msg = await ctx.send(embed=processing_embed)
    
    try:
        # Download
        lua_content = await attachment.read()
        lua_content = lua_content.decode('utf-8')
        
        # Obfuscate
        result, success, error_msg = await obfuscate_lua(lua_content, attachment.filename)
        
        # Delete processing message
        await processing_msg.delete()
        
        if success:
            output_filename = f"obf_{attachment.filename}"
            file = discord.File(fp=result, filename=output_filename)
            
            embed = discord.Embed(
                title="✅ Obfuscation Successful!",
                description="Your Lua script has been obfuscated!",
                color=discord.Color.green()
            )
            embed.add_field(name="📄 Input", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="🔒 Output", value=f"`{output_filename}`", inline=True)
            embed.add_field(
                name="📊 Size",
                value=f"{attachment.size:,} → {result.getbuffer().nbytes:,} bytes",
                inline=True
            )
            embed.set_footer(text="Powered by Ironbrew 2")
            
            await ctx.send(embed=embed, file=file)
        else:
            embed = discord.Embed(
                title="❌ Obfuscation Failed",
                description=f"```\n{error_msg[:1500]}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    except UnicodeDecodeError:
        await processing_msg.delete()
        await ctx.send("❌ Error: File is not valid UTF-8 text!")
    except Exception as e:
        try:
            await processing_msg.delete()
        except:
            pass
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='ping')
async def cmd_ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: `{latency}ms`")


@bot.command(name='help')
async def cmd_help(ctx):
    """Show help"""
    embed = discord.Embed(
        title="🔒 Ironbrew 2 - Lua Obfuscator Bot",
        description="Obfuscate your Lua scripts using Ironbrew 2",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📝 Commands",
        value=f"""
**Slash Commands:**
`/obfuscate` - Obfuscate a Lua file
`/ping` - Check latency
`/help` - Show help

**Prefix Commands:**
`{PREFIX}obfuscate` - Obfuscate (attach file)
`{PREFIX}ping` - Check latency
`{PREFIX}help` - Show help
        """,
        inline=False
    )
    embed.add_field(
        name="📎 How to Use",
        value="1. Attach `.lua` file\n2. Send with command\n3. Download result",
        inline=False
    )
    embed.set_footer(text="Ironbrew 2 | .NET 3.1 + Lua 5.1")
    
    await ctx.send(embed=embed)


@bot.command(name='sync')
async def cmd_sync(ctx):
    """Force sync slash commands (owner only)"""
    # Check if bot owner
    app_info = await bot.application_info()
    if ctx.author.id != app_info.owner.id:
        await ctx.send("❌ This command is only for bot owner!")
        return
    
    await ctx.send("⏳ Syncing slash commands...")
    
    try:
        # Clear and sync
        synced = await bot.tree.sync()
        
        # Sync to current guild too
        if ctx.guild:
            bot.tree.copy_global_to(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
        
        await ctx.send(f"✅ Synced {len(synced)} commands globally!")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


# ============================================
# Events
# ============================================
@bot.event
async def on_ready():
    print("=" * 50)
    print(f"  🔒 Ironbrew 2 Discord Bot")
    print(f"  Logged in as: {bot.user.name}")
    print(f"  Bot ID: {bot.user.id}")
    print(f"  Guilds: {len(bot.guilds)}")
    print(f"  Prefix: {PREFIX}")
    print("=" * 50)
    
    # Set presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"/help | {PREFIX}help"
        )
    )
    
    # ========================================
    # FORCE SYNC SLASH COMMANDS
    # ========================================
    print("\n[Sync] Syncing slash commands...")
    
    try:
        # Sync global
        synced = await bot.tree.sync()
        print(f"[Sync] ✅ Global: {len(synced)} commands")
        
        # Sync to each guild for instant availability
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"[Sync] ✅ Guild: {guild.name}")
            except Exception as e:
                print(f"[Sync] ❌ Guild {guild.name}: {e}")
                
    except Exception as e:
        print(f"[Sync] ❌ Error: {e}")
    
    print("\n🚀 Bot is ready!")
    print("=" * 50)


@bot.event
async def on_guild_join(guild):
    """Sync commands when joining new guild"""
    print(f"[Guild] Joined: {guild.name}")
    try:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"[Guild] ✅ Synced commands to {guild.name}")
    except Exception as e:
        print(f"[Guild] ❌ Failed to sync: {e}")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    else:
        print(f"[Error] {error}")
        await ctx.send(f"❌ An error occurred: {str(error)[:100]}")


# ============================================
# Main Entry Point
# ============================================
async def main():
    print("\n🚀 Starting Ironbrew 2 Discord Bot...")
    print(f"[Config] Token: {'*' * 10}...{TOKEN[-5:] if TOKEN else 'NOT SET'}")
    print(f"[Config] Prefix: {PREFIX}")
    print(f"[Config] Port: {PORT}")
    
    # Start health check server
    await start_health_server()
    
    # Start bot
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Bot] Shutting down...")
    except Exception as e:
        print(f"[Bot] Fatal error: {e}")
        raise
