"""Smoke-test Telethon login + upload (userbot and bot modes). No scraping.

Setup:
    cp .env.example .env   # then fill TG_API_ID/TG_API_HASH (+TG_BOT_TOKEN for bots)
    chmod 600 .env

Usage:
    python test_telegram.py --target me                        # userbot -> Saved Messages
    python test_telegram.py --mode bot --target -1001234567890  # bot -> channel/group
    python test_telegram.py --target me --file ./vid.mp4 --caption "hello"
Userbot first run asks for phone + code (and 2FA password), then saves session.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


async def _run(target: str, session: str, mode: str, bot_token: str | None,
               file: str | None, caption: str) -> None:
    from telethon import TelegramClient

    from xscraper.env import load_env

    load_env()
    api_id = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    mode = (mode or os.environ.get("TG_MODE", "userbot")).strip().lower()
    token = (bot_token or os.environ.get("TG_BOT_TOKEN", "")).strip() or None
    if not api_id or not api_hash:
        print("Set TG_API_ID and TG_API_HASH in .env (see .env.example).")
        raise SystemExit(2)
    if mode == "bot" and not token:
        print("Bot mode needs TG_BOT_TOKEN in .env or --bot-token.")
        raise SystemExit(2)
    sess = session or os.environ.get("TG_SESSION", "xscraper")
    tgt: str | int = target.strip()
    if tgt.lstrip("-").isdigit():
        tgt = int(tgt)
    if mode == "bot" and tgt == "me":
        print("Bots cannot use target 'me'. Use a chat/channel id.")
        raise SystemExit(2)
    client = TelegramClient(sess, int(api_id), api_hash)
    if mode == "bot":
        await client.start(bot_token=token)
    else:
        await client.start()
    async with client:
        me = await client.get_me()
        print(f"[{mode}] logged in as: {getattr(me, 'username', me)}")
        if file:
            await client.send_file(tgt, file, caption=caption, supports_streaming=True)
            print(f"Sent file {file} -> {target}")
        else:
            await client.send_message(tgt, caption or "✅ XProfileDownloader Telegram test")
            print(f"Sent test message -> {target}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Test Telegram/Telethon connection (userbot + bot).")
    p.add_argument("--target", default=os.environ.get("TG_TARGET", "me"))
    p.add_argument("--session", default=os.environ.get("TG_SESSION", "xscraper"))
    p.add_argument("--mode", default=None, choices=["userbot", "bot"], help="or TG_MODE")
    p.add_argument("--bot-token", default=None, help="or TG_BOT_TOKEN")
    p.add_argument("--env-file", default=None)
    p.add_argument("--file", default=None)
    p.add_argument("--caption", default="✅ XProfileDownloader Telegram test")
    a = p.parse_args(argv)
    if a.env_file:
        from xscraper.env import load_env

        load_env(a.env_file)
    if a.file and not Path(a.file).is_file():
        print(f"File not found: {a.file}")
        return 2
    asyncio.run(_run(a.target, a.session, a.mode or "userbot", a.bot_token, a.file, a.caption))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
