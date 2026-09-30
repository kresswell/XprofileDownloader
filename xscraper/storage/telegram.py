"""Telegram storage backend via Telethon (userbot + bot modes).

Flow per post: yt-dlp download to staging dir -> send_file to target chat.
Credentials come from .env / env, never code. See .env.example:
  TG_MODE=userbot|bot, TG_API_ID, TG_API_HASH,
  TG_SESSION (userbot), TG_BOT_TOKEN (bot), TG_TARGET (or --tg-target).
Get api_id/api_hash at https://my.telegram.org, bot token from @BotFather.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from loguru import logger

from xscraper.config import DownloadConfig, TelegramConfig
from xscraper.scraper import Post
from xscraper.storage.base import StorageResult
from xscraper.storage.local import DOWNLOADABLE, LocalStorage


def telegram_config_from_env(
    target: str | None = None,
    session: str | Path | None = None,
    keep_files: bool = True,
    mode: str | None = None,
    bot_token: str | None = None,
) -> TelegramConfig:
    from xscraper.env import load_env

    load_env()  # .env -> os.environ, real env wins
    api_id = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    tg_mode = (mode or os.environ.get("TG_MODE", "userbot")).strip().lower()
    tg_target = (target or os.environ.get("TG_TARGET", "")).strip()
    token = (bot_token or os.environ.get("TG_BOT_TOKEN", "")).strip() or None
    sess = str(session or os.environ.get("TG_SESSION", "")).strip() or "xscraper"
    if not api_id or not api_hash:
        raise RuntimeError("Set TG_API_ID and TG_API_HASH in .env (see .env.example).")
    if not tg_target:
        raise RuntimeError("Set Telegram target via --tg-target or TG_TARGET in .env (e.g. 'me').")
    if tg_mode == "bot" and not token:
        raise RuntimeError("Bot mode needs TG_BOT_TOKEN in .env or --tg-bot-token.")
    if tg_mode == "bot" and tg_target == "me":
        raise RuntimeError("Bots cannot use target 'me'. Use a chat/channel id where the bot is a member.")
    return TelegramConfig(
        api_id=int(api_id),
        api_hash=api_hash,
        target=_coerce_target(tg_target),
        mode=tg_mode,
        bot_token=token,
        session=Path(sess),
        keep_files=keep_files,
    )


def _coerce_target(t: str) -> str | int:
    t = t.strip()
    if t.lstrip("-").isdigit():
        return int(t)
    return t


class TelegramStorage:
    """Downloads with yt-dlp, uploads to Telegram. Implements MediaStorage."""

    def __init__(self, tg: TelegramConfig, dl: DownloadConfig, handle: str = "") -> None:
        self.tg = tg
        self.dl = dl
        self.handle = handle.lstrip("@")
        self._local = LocalStorage(dl)

    def store(self, posts: list[Post]) -> StorageResult:
        return asyncio.run(self._store_async(posts))

    async def _store_async(self, posts: list[Post]) -> StorageResult:
        from telethon import TelegramClient

        queue = [p for p in posts if p.kind in DOWNLOADABLE]
        result = StorageResult(skipped=len(posts) - len(queue))
        if not queue:
            return result

        self.dl.dl_dir.mkdir(parents=True, exist_ok=True)
        session_str = str(self.tg.session.with_suffix(""))  # telethon adds .session
        logger.info(f"Connecting Telegram [{self.tg.mode}] session '{session_str}' -> {self.tg.target}")
        client = TelegramClient(session_str, self.tg.api_id, self.tg.api_hash)
        if self.tg.mode == "bot":
            await client.start(bot_token=self.tg.bot_token)
        else:
            await client.start()  # userbot: phone+code on first run, then session file
        async with client:
            for i, post in enumerate(queue, 1):
                logger.info(f"[{i}/{len(queue)}] {post.url}")
                before = set(self.dl.dl_dir.iterdir()) if self.dl.dl_dir.exists() else set()
                # Prefix with tweet id so post -> files mapping is reliable
                # (yt-dlp's %(id)s is the media id, not the tweet id).
                self._local.config.template = (
                    f"{post.tweet_id}-%(id)s-%(autonumber)s.%(ext)s"
                )
                if not self._local.download_one(post.url):
                    result.failed += 1
                    continue
                new_files = sorted(
                    (f for f in self.dl.dl_dir.iterdir() if f not in before and f.is_file()),
                    key=lambda f: f.name,
                )
                if not new_files:
                    # Already downloaded (e.g. local pass ran first, --no-overwrites
                    # made yt-dlp a no-op): fall back to files for this tweet id.
                    existing = sorted(
                        (f for f in self.dl.dl_dir.glob(f"*{post.tweet_id}*") if f.is_file()),
                        key=lambda f: f.name,
                    )
                    if existing:
                        logger.info(f"Reusing {len(existing)} existing file(s) for {post.url}")
                        new_files = existing
                if not new_files:
                    logger.warning(f"No new files for {post.url}")
                    result.failed += 1
                    continue
                caption = self.tg.caption_template.format(
                    kind=post.kind, handle=self.handle, url=post.url
                )
                try:
                    for j, f in enumerate(new_files):
                        cap = caption if j == 0 else ""
                        await client.send_file(
                            self.tg.target, str(f), caption=cap, supports_streaming=True
                        )
                    result.ok += 1
                    if not self.tg.keep_files:
                        for f in new_files:
                            f.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"TG FAILED {post.url} :: {e}")
                    result.failed += 1
        logger.success(f"Telegram -> {self.tg.target}: {result.ok} ok, {result.failed} failed.")
        return result
