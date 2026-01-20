import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import aiohttp
from obfuscator import obfuscate_lua
from aiohttp import web

# ============================================
# Configuration
# ============================================
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('BOT_PREFIX', '!')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ============================================
# Health Check Server (Required by Render)
# ============================================
async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    port = int(os.getenv('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Health check server running on port {port}")

# ============================================
# Bot Events
# ============================================
@bot.event
async def on_ready():
    print(f'========================================')
    print(f'  Ironbrew 2 Discord Bot')
    print(f'  Logged in as: {bot.user.name}')
    print(f'  Bot ID: {bot.user.id}')
    print(f'========================================')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ============================================
# Commands
# ============================================

# Prefix Command: !obfuscate
@bot.command(name='obfuscate', aliases=['obf', 'ib2'])
async def obfuscate_command(ctx):
    """Obfuscate Lua file dengan Ironbrew 2"""
    
    if not ctx.message.attachments:
        embed = discord.Embed(
            title="❌ Error",
            description="Silakan lampirkan file `.lua` untuk di-obfuscate!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Cara Penggunaan",
            value=f"1. Ketik `{PREFIX}obfuscate`\n2. Lampirkan file `.lua`",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    attachment = ctx.message.attachments[0]
    
    # Validate file
    if not attachment.filename.endswith('.lua'):
        await ctx.send("❌ Hanya file `.lua` yang diterima!")
        return
    
    if attachment.size > 5 * 1024 * 1024:  # 5MB limit
        await ctx.send("❌ File terlalu besar! Maksimal 5MB.")
        return
    
    # Processing message
    processing_msg = await ctx.send("⏳ Sedang memproses obfuscation...")
    
    try:
        # Download file
        lua_content = await attachment.read()
        lua_content = lua_content.decode('utf-8')
        
        # Obfuscate
        result, success, error_msg = await obfuscate_lua(
            lua_content, 
            attachment.filename
        )
        
        if success:
            # Create output file
            output_filename = f"obfuscated_{attachment.filename}"
            
            # Send result
            file = discord.File(
                fp=result,
                filename=output_filename
            )
            
            embed = discord.Embed(
                title="✅ Obfuscation Berhasil!",
                description=f"File `{attachment.filename}` telah di-obfuscate.",
                color=discord.Color.green()
            )
            embed.add_field(name="Original", value=attachment.filename, inline=True)
            embed.add_field(name="Output", value=output_filename, inline=True)
            embed.set_footer(text="Powered by Ironbrew 2")
            
            await processing_msg.delete()
            await ctx.send(embed=embed, file=file)
        else:
            embed = discord.Embed(
                title="❌ Obfuscation Gagal",
                description=f"```\n{error_msg}\n```",
                color=discord.Color.red()
            )
            await processing_msg.delete()
            await ctx.send(embed=embed)
            
    except Exception as e:
        await processing_msg.delete()
        await ctx.send(f"❌ Error: {str(e)}")

# Slash Command: /obfuscate
@bot.tree.command(name="obfuscate", description="Obfuscate file Lua dengan Ironbrew 2")
async def slash_obfuscate(interaction: discord.Interaction, file: discord.Attachment):
    """Slash command untuk obfuscate"""
    
    # Validate
    if not file.filename.endswith('.lua'):
        await interaction.response.send_message("❌ Hanya file `.lua` yang diterima!", ephemeral=True)
        return
    
    if file.size > 5 * 1024 * 1024:
        await interaction.response.send_message("❌ File terlalu besar! Maksimal 5MB.", ephemeral=True)
        return
    
    await interaction.response.defer(thinking=True)
    
    try:
        lua_content = await file.read()
        lua_content = lua_content.decode('utf-8')
        
        result, success, error_msg = await obfuscate_lua(lua_content, file.filename)
        
        if success:
            output_filename = f"obfuscated_{file.filename}"
            discord_file = discord.File(fp=result, filename=output_filename)
            
            embed = discord.Embed(
                title="✅ Obfuscation Berhasil!",
                color=discord.Color.green()
            )
            embed.add_field(name="Original", value=file.filename, inline=True)
            embed.add_field(name="Output", value=output_filename, inline=True)
            
            await interaction.followup.send(embed=embed, file=discord_file)
        else:
            await interaction.followup.send(f"❌ Gagal: {error_msg}")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

# Help Command
@bot.command(name='help_ib2')
async def help_command(ctx):
    embed = discord.Embed(
        title="🔒 Ironbrew 2 - Lua Obfuscator Bot",
        description="Bot untuk mengobfuscate script Lua menggunakan Ironbrew 2",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f"📝 Commands",
        value=f"""
`{PREFIX}obfuscate` - Obfuscate file Lua (lampirkan file)
`{PREFIX}help_ib2` - Tampilkan bantuan ini
`/obfuscate` - Slash command untuk obfuscate
        """,
        inline=False
    )
    embed.add_field(
        name="📎 Cara Penggunaan",
        value="1. Lampirkan file `.lua`\n2. Kirim dengan command `!obfuscate`",
        inline=False
    )
    embed.set_footer(text="Powered by Ironbrew 2 | .NET 3.1 + Lua 5.1")
    
    await ctx.send(embed=embed)

# ============================================
# Main
# ============================================
async def main():
    # Start health check server
    await start_health_server()
    
    # Start bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
