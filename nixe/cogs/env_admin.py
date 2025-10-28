
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, json, logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

SENSITIVE_RX = re.compile(r"(TOKEN|SECRET|KEY|PASSWORD|PASS|WEBHOOK|PRIVATE)", re.I)
DEFAULT_PATH = os.getenv("NIXE_CONFIG_PATH", "nixe/config/runtime_env.json")

def _redact(k: str, v: str) -> str:
    if SENSITIVE_RX.search(k):
        if not v:
            return ""
        if len(v) <= 8:
            return "*" * len(v)
        return v[:3] + "*" * (len(v)-6) + v[-3:]
    return v

class EnvAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.command(name="env-reload")
    async def env_reload(self, ctx: commands.Context, path: str | None = None, override: str = "1"):
        """Reload JSON env into process env. Usage: &env-reload [path] [override: 1|0]"""
        from nixe.env_bootstrap import apply_env_from_json
        p = path or DEFAULT_PATH
        ov = (override == "1")
        n = apply_env_from_json(p, override=ov)
        await ctx.reply(f"env-reload: applied {n} key(s) from `{p}` (override={ov})", mention_author=False)

    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.command(name="env-show")
    async def env_show(self, ctx: commands.Context, key: str):
        """Show one env key (redacted if sensitive)."""
        v = os.getenv(key, "")
        await ctx.reply(f"{key} = `{_redact(key, v)}`", mention_author=False)

    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.command(name="env-dump")
    async def env_dump(self, ctx: commands.Context, prefix: str = ""):
        """Dump current env (filtered; optionally by prefix)."""
        items = []
        for k in sorted(os.environ.keys()):
            if prefix and not k.startswith(prefix):
                continue
            items.append(f"{k}={_redact(k, os.environ.get(k, ''))}")
            if len(items) >= 80:
                break
        fence = "```"
        txt = f"{fence}\n" + "\n".join(items) + f"\n{fence}"
        await ctx.reply(txt, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(EnvAdmin(bot))
