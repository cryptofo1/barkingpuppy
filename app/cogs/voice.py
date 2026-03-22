import logging

from discord.ext import commands, tasks

from app.database import async_session
from app.services.cooldown import check_hourly_cap
from app.services.leveling import add_xp

log = logging.getLogger("barkingpuppy.voice")

XP_PER_MINUTE = 5


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.voice_xp_loop.start()

    def cog_unload(self) -> None:
        self.voice_xp_loop.cancel()

    @tasks.loop(minutes=1)
    async def voice_xp_loop(self) -> None:
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                eligible = [
                    m for m in vc.members
                    if not m.bot
                    and not m.voice.self_mute
                    and not m.voice.mute
                ]
                if len(eligible) < 2:
                    continue

                for member in eligible:
                    xp = await check_hourly_cap(member.id, guild.id, XP_PER_MINUTE)
                    if xp <= 0:
                        continue

                    async with async_session() as session:
                        user, leveled_up = await add_xp(session, member.id, guild.id, xp)

                    if leveled_up:
                        log.info(
                            "Voice level-up: %s reached level %d in %s",
                            member, user.level, guild.name,
                        )

    @voice_xp_loop.before_loop
    async def before_voice_xp(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot))
