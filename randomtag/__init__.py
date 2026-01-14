from .randomtag import RandomTag

async def setup(bot):
    # This ensures the cog is properly added to Red's registry
    await bot.add_cog(RandomTag(bot))
