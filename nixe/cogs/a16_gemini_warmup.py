from __future__ import annotations
import asyncio, os
from discord.ext import commands

class GeminiWarmup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        await self.bot.wait_until_ready()
        try:
            tout = int(os.getenv("LUCKYPULL_GEM_TIMEOUT_MS","20000"))
        except Exception:
            tout = 20000

        # Try to generate a valid 128x128 RGB JPEG (avoid 1x1 PNG which breaks Gemini)
        img_bytes = None
        try:
            from io import BytesIO
            try:
                from PIL import Image, ImageDraw
            except Exception:
                Image = None
            if Image is not None:
                im = Image.new("RGB", (128,128), (32,32,32))
                dr = ImageDraw.Draw(im)
                dr.rectangle((16,16,112,112), outline=(200,200,200), width=2)
                buf = BytesIO()
                im.save(buf, "JPEG", quality=85, optimize=True)
                img_bytes = buf.getvalue()
        except Exception as _e:
            img_bytes = None

        try:
            import nixe.helpers.gemini_bridge as gb  # will be safety-patched by a16_gemini_safety_patch
            images = [img_bytes] if img_bytes else None
            label, conf = await gb.classify_lucky_pull(images, hints="warmup", timeout_ms=tout)
            meta = getattr(gb, "LAST_META", {})
            fb = meta.get("fallback", False)
            if getattr(self.bot, "logger", None):
                self.bot.logger.info("[gemini-warmup] label=%s conf=%.3f fallback=%s", label, float(conf), fb)
        except Exception as e:
            # Never escalate on warmup
            if getattr(self.bot, "logger", None):
                self.bot.logger.info("[gemini-warmup] skipped or neutral: %r", e)

async def setup(bot):
    await bot.add_cog(GeminiWarmup(bot))
