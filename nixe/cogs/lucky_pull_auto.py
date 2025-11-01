# nixe/cogs/lucky_pull_auto.py
# LPA with "provider-first" policy. Nixe executes only after Groq/Gemini classification.
import os, time
from typing import Tuple, Optional
import discord
from discord.ext import commands

def _getenv(k: str, d: str = "") -> str:
    return os.getenv(k, d)

def _split_csv(v: str):
    return [x.strip() for x in (v or "").split(",") if x.strip()]

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = _getenv("LPA_ENABLE","1") == "1"
        self.delete_on_match = _getenv("LPA_DELETE_ON_MATCH","1") == "1"
        self.guard_channels = set(_split_csv(_getenv("LPA_GUARD_CHANNELS","")))
        self.redirect_channel_id = int(_getenv("LPA_REDIRECT_CHANNEL_ID","0") or 0)
        self.thr = float(_getenv("LPA_THRESHOLD_DELETE","0.85") or 0.85)
        self.cooldown_sec = int(_getenv("LPA_COOLDOWN_SEC","10") or 10)

        # Provider-first knobs
        self.exec_mode = _getenv("LPA_EXECUTION_MODE","provider_first")  # provider_first|hybrid|heuristic_only
        self.defer_if_provider_down = _getenv("LPA_DEFER_IF_PROVIDER_DOWN","1") == "1"
        self.provider_order = _getenv("LPA_PROVIDER_ORDER","groq,gemini")

        # Lightweight heuristics (used only in 'hybrid' as a weak hint)
        self.req_kw_if_model_down = _getenv("LPA_REQUIRE_KEYWORD_IF_MODEL_DOWN","1") == "1"
        self.fallback_score = float(_getenv("LPA_FALLBACK_SCORE","0.0") or 0.0)

        self._cool = {}

        # Optional provider bridge
        self.bridge = None
        try:
            from nixe.helpers import lpa_provider_bridge as BR
            self.bridge = BR
        except Exception as e:
            self.bridge = None

        # Optional heuristics
        self.H = None
        try:
            from nixe.helpers import lpa_heuristics as H
            self.H = H
        except Exception:
            self.H = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled:
            print("WARNING:nixe.cogs.lucky_pull_auto:disabled via ENV"); return
        print(f"INFO:nixe.cogs.lucky_pull_auto:mode={self.exec_mode} thr={self.thr} defer_if_provider_down={self.defer_if_provider_down} provider_order={self.provider_order}")

    def _in_scope(self, ch: discord.abc.GuildChannel) -> bool:
        return True if not self.guard_channels else str(ch.id) in self.guard_channels

    def _cool_ok(self, ch_id: int, au_id: int) -> bool:
        now = time.time(); key = (ch_id, au_id); last = self._cool.get(key, 0.0)
        if now - last < self.cooldown_sec: return False
        self._cool[key] = now; return True

    def _collect(self, m: discord.Message) -> str:
        parts = [m.content or ""]
        for e in m.embeds:
            if e.title: parts.append(e.title)
            if e.description: parts.append(e.description)
            if e.url: parts.append(e.url)
            if e.footer and e.footer.text: parts.append(e.footer.text)
            for f in e.fields or []:
                parts.append(f.name or ""); parts.append(f.value or "")
        for a in m.attachments:
            if a.filename: parts.append(a.filename)
        return "\n".join(parts).strip()

    def _heuristic_score(self, text: str) -> float:
        if not self.H: return 0.0
        score, kw, neg = self.H.score_text_basic(text)
        if self.req_kw_if_model_down and kw == 0:
            return 0.0
        return max(self.fallback_score, score)

    def _provider_score(self, text: str):
        if not self.bridge:
            return None, "no_bridge"
        sc, reason = self.bridge.classify(text, self.provider_order)
        return sc, reason

    async def _log(self, guild, ch_id, author, prob, reason, action, preview):
        ch = guild.get_channel(self.redirect_channel_id) if self.redirect_channel_id else None
        if not isinstance(ch,(discord.TextChannel, discord.Thread)): return
        if len(preview) > 400: preview = preview[:400] + "…"
        try:
            await ch.send(f"[lpa] {action} in <#{ch_id}> by {author} | prob={prob if prob is not None else 'None'} thr={self.thr} reason={reason}\nPreview:\n```{preview or '(no text)'}\n```")
        except Exception as e:
            print(f"WARNING:nixe.cogs.lucky_pull_auto:log failed: {e!r}")

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not self.enabled or not m.guild or m.author.bot: return
        if not self._in_scope(m.channel): return
        if not self._cool_ok(m.channel.id, m.author.id): return

        text = self._collect(m)
        reason = "init"
        prob: Optional[float] = None

        if self.exec_mode == "provider_first":
            prob, reason = self._provider_score(text)
            if prob is None:
                # Provider unavailable; either defer or fall back
                if self.defer_if_provider_down:
                    await self._log(m.guild, m.channel.id, m.author, prob, reason, "Deferred (provider down)", text)
                    return
                else:
                    prob = self._heuristic_score(text); reason = "fallback_heuristic"
        elif self.exec_mode == "hybrid":
            # Look at provider; if down, use heuristic
            prob, reason = self._provider_score(text)
            if prob is None:
                prob = self._heuristic_score(text); reason = "fallback_heuristic"
        else:  # heuristic_only
            prob = self._heuristic_score(text); reason = "heuristic_only"

        # Execute
        action = "Skipped (below thr)"
        if prob is not None and prob >= self.thr and self.delete_on_match:
            try:
                await m.delete(); action = "Deleted (lucky pull)"
            except Exception as e:
                action = f"Delete failed: {e!r}"
        await self._log(m.guild, m.channel.id, m.author, prob, reason, action, text)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
