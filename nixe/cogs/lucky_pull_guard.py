# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from pathlib import Path
import discord
from discord.ext import commands

def _get_env(key: str, default: str = "0") -> str:
    v = os.getenv(key)
    if v is not None:
        return v
    try:
        envp = Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"
        data = json.loads(envp.read_text(encoding="utf-8"))
        v = data.get(key, default)
        return "" if v is None else str(v)
    except Exception:
        return default

DELETE_ON_GUARD = _get_env("LUCKYPULL_DELETE_ON_GUARD","0").strip() == "1"

async def _nixe_delete_and_mention(bot, message: discord.Message, redirect_id: int):
    try:
        await message.delete()
    except Exception:
        pass
    dest = None
    try:
        dest = message.guild.get_channel(redirect_id)
    except Exception:
        dest = None
    mention = message.author.mention if getattr(message, "author", None) else ""
    text = f"{mention} lucky pull pindah ke <#{redirect_id}> ya 🙏" if dest is None else            f"{mention} lucky pull pindah ke {dest.mention} ya 🙏"
    try:
        await message.channel.send(text, delete_after=15)
    except Exception:
        pass

class LuckyPullDeleteMentionEnforcer(commands.Cog):
    """Core behavior: delete user post in guard channels and mention to redirect channel."""
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not DELETE_ON_GUARD or not message or (getattr(message, "author", None) and message.author.bot):
            return
        try:
            guards = [s.strip() for s in _get_env("LUCKYPULL_GUARD_CHANNELS","").split(",") if s.strip().isdigit()]
            redirect_id = int((_get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or "0").strip())
            if not redirect_id:
                return
            if message.channel and message.channel.id == redirect_id:
                return  # anti loop
            if str(message.channel.id) in guards:
                await _nixe_delete_and_mention(self.bot, message, redirect_id)
        except Exception:
            pass

# Backward-compat alias expected by loader(s)
class LuckyPullGuard(LuckyPullDeleteMentionEnforcer):
    pass

# IMPORTANT: let loader decide adding the Cog to avoid duplicates.
async def setup(bot):
    # If there is no dedicated loader, we can add once here.
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"):
        return
    try:
        await bot.add_cog(LuckyPullDeleteMentionEnforcer(bot))
    except Exception:
        pass
