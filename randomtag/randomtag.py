import random
import discord
import logging
from datetime import datetime, timedelta

from redbot.core import commands, Config
from discord.ext import tasks

log = logging.getLogger("red.seina.randomtag")


class RandomTag(commands.Cog):
    """Automated random tag posting compatible with Seina-Cogs Tags."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=998877665544, force_registration=True)
        default_guild = {
            "channel_id": None,
            "last_post": 0.0,  # Unix timestamp of last post
        }
        self.config.register_guild(**default_guild)
        self.daily_loop.start()

    def cog_unload(self):
        self.daily_loop.cancel()

    @tasks.loop(minutes=30)
    async def daily_loop(self):
        """Check every 30 minutes and post a tag if 24h passed."""
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            return

        # Prefer aware datetimes using Discord's epoch
        now = datetime.utcnow()

        for guild in self.bot.guilds:
            conf = await self.config.guild(guild).all()
            channel_id = conf.get("channel_id")
            last_post_ts = conf.get("last_post", 0.0)

            if not channel_id:
                continue

            # Check 24h cooldown
            if last_post_ts:
                last_post_time = datetime.utcfromtimestamp(last_post_ts)
                if now < last_post_time + timedelta(hours=24):
                    continue

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            # Seina Tags uses in-memory caches like guild_tag_cache and global_tag_cache
            guild_cache = getattr(tags_cog, "guild_tag_cache", {}).get(guild.id, {})
            global_cache = getattr(tags_cog, "global_tag_cache", {})

            # Tag objects (keys are names, values are Tag objects)
            all_tags = list(guild_cache.values()) + list(global_cache.values())
            if not all_tags:
                continue

            tag_to_send = random.choice(all_tags)

            try:
                # Seina’s Tags exposes process_tag(ctx_or_channel, tag, **kwargs)
                # Using author=guild.me so tags referring to {author} work
                await tags_cog.process_tag(channel, tag_to_send, author=guild.me)
                await self.config.guild(guild).last_post.set(now.timestamp())
            except Exception as e:
                log.error("Error auto-posting tag in %s: %r", guild.id, e)

    @daily_loop.before_loop
    async def before_daily_loop(self):
        await self.bot.wait_until_ready()

    @commands.group()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def tagschedule(self, ctx: commands.Context):
        """Manage 24-hour random tag posting."""
        if ctx.invoked_subcommand is None:
            conf = await self.config.guild(ctx.guild).all()
            channel_id = conf.get("channel_id")
            last_post_ts = conf.get("last_post", 0.0)

            channel_display = "Disabled"
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channel_display = f"{channel.mention} (ID: {channel.id})"

            last_post_display = "Never"
            if last_post_ts:
                dt = datetime.utcfromtimestamp(last_post_ts)
                last_post_display = f"{discord.utils.format_dt(dt, style='R')}"

            await ctx.send(
                f"Current daily tag channel: {channel_display}\n"
                f"Last automatic post: {last_post_display}"
            )

    @tagschedule.command(name="channel")
    @commands.guild_only()
    async def tagschedule_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel for daily tags. Leave empty to disable."""
        if channel:
            await self.config.guild(ctx.guild).channel_id.set(channel.id)
            await ctx.send(f"✅ Daily tags enabled in {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).channel_id.set(None)
            await ctx.send("❌ Daily tags disabled.")

    @commands.command()
    @commands.guild_only()
    async def tagrandom(self, ctx: commands.Context):
        """Manually trigger a random tag using Seina Tags."""
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            await ctx.send("The Tags cog is not loaded.")
            return

        guild_cache = getattr(tags_cog, "guild_tag_cache", {}).get(ctx.guild.id, {})
        global_cache = getattr(tags_cog, "global_tag_cache", {})

        all_tags = list(guild_cache.values()) + list(global_cache.values())
        if not all_tags:
            await ctx.send("No tags found for this server or globally.")
            return

        tag_to_send = random.choice(all_tags)
        # Use ctx as first argument to match Seina’s process_tag signature
        await tags_cog.process_tag(ctx, tag_to_send)

async def setup(bot):
    await bot.add_cog(RandomTag(bot))
