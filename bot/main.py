"""
Ironbrew 2 Discord Bot
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from aiohttp import web

from obfuscator import obfuscate_lua

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('BOT_PREFIX', '!')
PORT = int(os.getenv('PORT', 10000))

if not TOKEN:
    print("ERROR: DISCORD_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# Health check for Render
async def health_handler(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', health_handler)
    app.router.add_get('/health', health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"[Health] Server on port {PORT}")


# Slash Commands
@bot.tree.command(name="obfuscate", description="Obfuscate a Lua file with Ironbrew 2")
@app_commands.describe(file="The .lua file to obfuscate")
async def slash_obfuscate(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith('.lua'):
        await interaction.response.send_message("❌ Only `.lua` files!", ephemeral=True)
        return
    
    if file.size > 2 * 1024 * 1024:
        await interaction.response.send_message("❌ Max 2MB!", ephemeral=True)
        return
    
    await interaction.response.defer(thinking=True)
    
    try:
        content = await file.read()
        content = content.decode('utf-8')
        
        result, success, error = await obfuscate_lua(content, file.filename)
        
        if success:
            out_name = f"obf_{file.filename}"
            discord_file = discord.File(fp=result, filename=out_name)
            
            embed = discord.Embed(title="✅ Obfuscation Successful!", color=discord.Color.green())
            embed.add_field(name="Input", value=f"`{file.filename}`", inline=True)
            embed.add_field(name="Output", value=f"`{out_name}`", inline=True)
            embed.set_footer(text="Powered by Ironbrew 2")
            
            await interaction.followup.send(embed=embed, file=discord_file)
        else:
            await interaction.followup.send(f"❌ Failed:\n```\n{error[:1500]}\n```")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency*1000)}ms")


@bot.tree.command(name="help", description="Show help")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🔒 Ironbrew 2 Bot", color=discord.Color.blue())
    embed.add_field(name="Commands", value="`/obfuscate` - Obfuscate Lua\n`/ping` - Latency\n`/help` - Help", inline=False)
    embed.add_field(name="Usage", value="1. Use `/obfuscate`\n2. Attach `.lua` file\n3. Get obfuscated result", inline=False)
    await interaction.response.send_message(embed=embed)


# Prefix Commands
@bot.command(name='obfuscate', aliases=['obf', 'ib2'])
async def cmd_obfuscate(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ Attach a `.lua` file!")
        return
    
    att = ctx.message.attachments[0]
    if not att.filename.lower().endswith('.lua'):
        await ctx.send("❌ Only `.lua` files!")
        return
    
    msg = await ctx.send("⏳ Processing...")
    
    try:
        content = await att.read()
        content = content.decode('utf-8')
        
        result, success, error = await obfuscate_lua(content, att.filename)
        
        await msg.delete()
        
        if success:
            out_name = f"obf_{att.filename}"
            file = discord.File(fp=result, filename=out_name)
            embed = discord.Embed(title="✅ Success!", color=discord.Color.green())
            embed.add_field(name="Input", value=f"`{att.filename}`", inline=True)
            embed.add_field(name="Output", value=f"`{out_name}`", inline=True)
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(f"❌ Failed:\n```\n{error[:1500]}\n```")
    except Exception as e:
        await msg.delete()
        await ctx.send(f"❌ Error: {e}")


@bot.command(name='ping')
async def cmd_ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency*1000)}ms")


@bot.command(name='help')
async def cmd_help(ctx):
    embed = discord.Embed(title="🔒 Ironbrew 2 Bot", color=discord.Color.blue())
    embed.add_field(name="Commands", value=f"`{PREFIX}obfuscate` - Obfuscate\n`{PREFIX}ping` - Latency\n`/obfuscate` - Slash", inline=False)
    await ctx.send(embed=embed)


@bot.command(name='sync')
async def cmd_sync(ctx):
    app = await bot.application_info()
    if ctx.author.id != app.owner.id:
        return
    
    await ctx.send("⏳ Syncing...")
    synced = await bot.tree.sync()
    for g in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=g)
            await bot.tree.sync(guild=g)
        except:
            pass
    await ctx.send(f"✅ Synced {len(synced)} commands!")


@bot.event
async def on_ready():
    print(f"{'='*50}")
    print(f"  Ironbrew 2 Discord Bot")
    print(f"  Logged in as: {bot.user}")
    print(f"  Guilds: {len(bot.guilds)}")
    print(f"{'='*50}")
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help"))
    
    # Sync slash commands
    print("[Sync] Syncing commands...")
    try:
        synced = await bot.tree.sync()
        print(f"[Sync] Global: {len(synced)}")
        for g in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=g)
                await bot.tree.sync(guild=g)
                print(f"[Sync] Guild: {g.name}")
            except:
                pass
    except Exception as e:
        print(f"[Sync] Error: {e}")
    
    print("Bot ready!")


async def main():
    print("Starting bot...")
    await start_health_server()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
