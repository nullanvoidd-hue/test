import random
import discord
import logging
from datetime import datetime, timedelta
from redbot.core import commands, Config
from discord.ext import tasks

log = logging.getLogger("red.seina.randomtag")

class RandomTag(commands.Cog):
    """Automated random tag posting compatible with Seina-Cogs."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=998877665544)
        default_guild = {
            "channel_id": None,
            "last_post": 0  # Stores timestamp of last post
        }
        self.config.register_guild(**default_guild)
        self.daily_loop.start()

    def cog_unload(self):
        self.daily_loop.cancel()

    @tasks.loop(minutes=30)  # Check every 30 mins to see if 24h have passed
    async def daily_loop(self):
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            return

        for guild in self.bot.guilds:
            conf = await self.config.guild(guild).all()
            if not conf["channel_id"]:
                continue

            # Check if 24 hours have passed since last_post
            last_post_time = datetime.fromtimestamp(conf["last_post"])
            if datetime.now() < last_post_time + timedelta(hours=24):
                continue

            channel = guild.get_channel(conf["channel_id"])
            if not channel:
                continue

            # Compatibility: Pull from Seina's internal defaultdict caches
            guild_cache = tags_cog.guild_tag_cache.get(guild.id, {})
            global_cache = tags_cog.global_tag_cache
            
            # Combine all available Tag objects
            all_tags = list(guild_cache.values()) + list(global_cache.values())

            if all_tags:
                tag_to_send = random.choice(all_tags)
                try:
                    # Using Seina's Processor mixin method
                    # author=guild.me ensures TagScript variables like {author} don't break
                    await tags_cog.process_tag(channel, tag_to_send, author=guild.me)
                    await self.config.guild(guild).last_post.set(datetime.now().timestamp())
                except Exception as e:
                    log.error(f"Error auto-posting tag in {guild.id}: {e}")

    @daily_loop.before_loop
    async def before_daily_loop(self):
        await self.bot.wait_until_ready()

    @commands.group()
    @commands.admin_or_permissions(manage_guild=True)
    async def tagschedule(self, ctx):
        """Manage 24-hour random tag posting."""
        pass

    @tagschedule.command(name="channel")
    async def set_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for daily tags. Leave empty to disable."""
        if channel:
            await self.config.guild(ctx.guild).channel_id.set(channel.id)
            await ctx.send(f"✅ Daily tags enabled in {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("❌ Daily tags disabled.")

    @commands.command()
    @commands.guild_only()
    async def tagrandom(self, ctx):
        """Manually trigger a random tag."""
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            return await ctx.send("The Tags cog is not loaded.")

        guild_cache = tags_cog.guild_tag_cache.get(ctx.guild.id, {})
        all_tags = list(guild_cache.values()) + list(tags_cog.global_tag_cache.values())
        
        if not all_tags:
            return await ctx.send("No tags found for this server or globally.")
        
        await tags_cog.process_tag(ctx, random.choice(all_tags))

async def setup(bot):
    await bot.add_cog(RandomTag(bot))
