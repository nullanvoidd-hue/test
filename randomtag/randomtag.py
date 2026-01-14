import random
import discord
from redbot.core import commands, Config
from discord.ext import tasks
import logging

log = logging.getLogger("red.seina.randomtag")

class RandomTag(commands.Cog):
    """Automated random tag posting for Seina-Cogs Tags."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=723489569234, force_registration=True)
        default_guild = {"channel_id": None}
        self.config.register_guild(**default_guild)
        self.daily_post.start()

    def cog_unload(self):
        self.daily_post.cancel()

    @tasks.loop(hours=24)
    async def daily_post(self):
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            log.warning("RandomTag loop skipped: Tags cog not loaded.")
            return

        for guild in self.bot.guilds:
            channel_id = await self.config.guild(guild).channel_id()
            if not channel_id:
                continue

            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            # Get tags from Seina's internal cache
            guild_cache = tags_cog.guild_tag_cache.get(guild.id, {})
            global_cache = tags_cog.global_tag_cache
            
            all_tags = list(guild_cache.values()) + list(global_cache.values())

            if all_tags:
                tag = random.choice(all_tags)
                
                # Seina-Cogs process_tag needs a context-like object. 
                # We use the bot as the 'author' for automatic posts.
                try:
                    await tags_cog.process_tag(channel, tag, author=guild.me)
                except Exception as e:
                    log.error(f"Failed to post daily tag in {guild.id}: {e}")

    @daily_post.before_loop
    async def before_daily_post(self):
        await self.bot.wait_until_ready()

    @commands.group()
    @commands.admin_or_permissions(manage_guild=True)
    async def tagschedule(self, ctx):
        """Configure daily tag posting."""
        pass

    @tagschedule.command()
    async def setchannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for the daily tag. Use without arguments to disable."""
        if channel:
            await self.config.guild(ctx.guild).channel_id.set(channel.id)
            await ctx.send(f"✅ Daily tags will be posted in {channel.mention} every 24 hours.")
        else:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("❌ Daily tag posting disabled.")

    @commands.command()
    @commands.guild_only()
    async def tagrandom(self, ctx):
        """Manually post a random tag right now."""
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            return await ctx.send("Tags cog is not loaded.")

        guild_cache = tags_cog.guild_tag_cache.get(ctx.guild.id, {})
        all_tags = list(guild_cache.values()) + list(tags_cog.global_tag_cache.values())
        
        if not all_tags:
            return await ctx.send("No tags found.")
        
        await tags_cog.process_tag(ctx, random.choice(all_tags))

async def setup(bot):
    await bot.add_cog(RandomTag(bot))
