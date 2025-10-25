import os, json, time, argparse, asyncio, platform, contextlib
import discord

# --- Windows event loop policy fix ---
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

def require(flag: str):
    v = os.getenv(flag, "0")
    return v == "1" or v.lower() in {"true","yes","y"}

def build_args():
    p = argparse.ArgumentParser(description="Create/adopt pHash DB message (text, no embed).")
    p.add_argument("--yes", action="store_true", help="Confirm creation if not found (required)")
    p.add_argument("--token", default=os.getenv("DISCORD_TOKEN"), help="Discord bot token (or env DISCORD_TOKEN)")
    p.add_argument("--thread", type=int, default=int(os.getenv("NIXE_PHASH_DB_THREAD_ID", "1431192568221270108")),
                   help="Target thread id (default from env)")
    p.add_argument("--src", type=int, default=int(os.getenv("NIXE_PHASH_SOURCE_THREAD_ID", "1409949797313679492")),
                   help="Source image thread id (default from env)")
    p.add_argument("--marker", default=(os.getenv("PHASH_DB_MARKER") or "NIXE_PHASH_DB_V1").strip(),
                   help="Marker line (default from env)")
    return p.parse_args()

async def run_once(args):
    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    done = asyncio.Event()

    async def _work():
        thread = client.get_channel(args.thread) or await client.fetch_channel(args.thread)
        # adopt if exists (ignore embeds)
        async for m in thread.history(limit=150, oldest_first=False):
            if m.author.id != client.user.id:
                continue
            if m.embeds:
                continue
            first = (m.content or "").splitlines()[0:1]
            if first and first[0].strip() == args.marker:
                print(f"[OK] DB sudah ada (msg_id={m.id}) — tidak membuat baru.")
                return

        payload = {
            "meta": {
                "marker": args.marker,
                "source_thread_id": args.src,
                "created_at": int(time.time()),
                "created_by": "nixe-cli"
            },
            "phash": []
        }
        content = args.marker + "\n" + json.dumps(payload, indent=2, ensure_ascii=False)
        msg = await getattr(thread, "send")(content)
        with contextlib.suppress(Exception):
            await getattr(msg, "pin")()
        print(f"[OK] DB baru dibuat: msg_id={msg.id} di thread={args.thread}")

    @client.event
    async def on_ready():
        try:
            await _work()
        finally:
            # signal main runner we're done; the runner will close the client
            done.set()

    # Explicit login/connect so we can control shutdown sequence
    await client.login(args.token)
    runner = asyncio.create_task(client.connect(reconnect=False))
    try:
        await done.wait()
        # graceful shutdown
        with contextlib.suppress(Exception):
            await client.close()
        with contextlib.suppress(Exception):
            await client.http.close()
        await asyncio.sleep(0.2)
    finally:
        # wait runner to finish or cancel
        if not runner.done():
            runner.cancel()
            with contextlib.suppress(Exception):
                await runner
        await asyncio.sleep(0.1)

def main():
    args = build_args()
    if not args.token:
        raise SystemExit("DISCORD_TOKEN tidak di-set (atau --token tidak diberikan).")
    if not (args.yes and require("NIXE_FORCE_DB_CLI")):
        raise SystemExit("CLI dinonaktifkan. Set NIXE_FORCE_DB_CLI=1 dan jalankan dengan --yes.")
    asyncio.run(run_once(args))

if __name__ == "__main__":
    main()
