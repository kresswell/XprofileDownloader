"""CLI - argparse wrapper preserving legacy positional args."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from xscraper.config import DownloadConfig, ScraperConfig
from xscraper.cookies import load_cookies, resolve_cookies_file
from xscraper.scraper import XProfileScraper
from xscraper.storage.local import LocalStorage, default_dl_dir


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Collect X profile post links and download media.")
    p.add_argument("handle", help="profile without @, e.g. heysavhere")
    p.add_argument("limit", nargs="?", type=int, default=50, help="max links (default 50)")
    p.add_argument("tab", nargs="?", default="media", help="media (default) or tweets")
    p.add_argument("out", nargs="?", default=None, help="txt export file (default <handle>.txt)")
    p.add_argument("only", nargs="?", default="", help="kind filter: video|photo|gif|mixed|text")
    p.add_argument(
        "dl_dir",
        nargs="?",
        default="",
        help="download folder, or 'download' for <handle>_downloads",
    )
    p.add_argument("--cookies", dest="cookies_file", default=None, help="path to Netscape cookies.txt")
    p.add_argument("--headful", action="store_true", help="show browser window")
    p.add_argument("--to-telegram", action="store_true", help="upload downloads to Telegram via Telethon")
    p.add_argument("--tg-target", default=None, help="Telegram target: 'me', @user, chat id (or TG_TARGET)")
    p.add_argument("--tg-session", default=None, help="Telethon session name/path (or TG_SESSION, default xscraper)")
    p.add_argument("--tg-clean", action="store_true", help="delete local files after Telegram upload")
    p.add_argument("--tg-mode", default=None, choices=["userbot", "bot"], help="Telegram mode (or TG_MODE)")
    p.add_argument("--tg-bot-token", default=None, help="Bot token for bot mode (or TG_BOT_TOKEN)")
    p.add_argument("--env-file", default=None, help="path to .env (default ./.env)")
    return p


def export_links(posts, out: Path) -> None:
    out.write_text("\n".join(p.url for p in posts) + ("\n" if posts else ""), encoding="utf-8")
    logger.success(f"Exported {len(posts)} links to {out}")


def run_config(cfg: ScraperConfig) -> int:
    cookies = load_cookies(cfg.cookies_file) if cfg.cookies_file else []
    if not cookies:
        logger.warning("No cookies file - continuing unauthenticated (expect login walls).")
    scraper = XProfileScraper(cookies=cookies, headless=cfg.headless)
    posts = scraper.collect(cfg.handle, limit=cfg.limit, tab=cfg.tab)
    if cfg.only:
        posts = [p for p in posts if p.kind == cfg.only]
    logger.success(f"{len(posts)} post links for @{cfg.handle}:")
    for post in posts:
        print(f"[{post.kind}] {post.url}")
    if cfg.out:
        export_links(posts, cfg.out)
    if cfg.to_telegram:
        from xscraper.storage.telegram import TelegramStorage, telegram_config_from_env

        staging = cfg.dl_dir or Path(f"{cfg.handle}_telegram_staging")
        tg = telegram_config_from_env(
            target=cfg.tg_target,
            session=cfg.tg_session,
            keep_files=cfg.tg_keep_files,
            mode=cfg.tg_mode,
            bot_token=cfg.tg_bot_token,
        )
        tstorage = TelegramStorage(tg=tg, dl=DownloadConfig(dl_dir=staging), handle=cfg.handle)
        tstorage.store(posts)
    elif cfg.dl_dir:
        storage = LocalStorage(DownloadConfig(dl_dir=cfg.dl_dir))
        res = storage.store(posts)
        logger.success(f"Downloads -> {cfg.dl_dir}: {res.ok} ok, {res.failed} failed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from xscraper.env import load_env

    load_env(args.env_file)  # .env -> env, real env wins
    resolved = args.cookies_file or resolve_cookies_file()
    if args.dl_dir and args.dl_dir != "" and args.dl_dir != "download":
        dl_dir = Path(args.dl_dir)
    elif args.dl_dir == "download":
        dl_dir = Path(f"{args.handle.lstrip('@')}_downloads")
    else:
        dl_dir = default_dl_dir(args.handle.lstrip("@"), args.dl_dir)

    cfg = ScraperConfig(
        handle=args.handle,
        limit=args.limit,
        tab=args.tab,
        only=args.only or "",
        out=Path(args.out) if args.out else Path(f"{args.handle.lstrip('@')}.txt"),
        dl_dir=dl_dir,
        cookies_file=Path(resolved) if resolved else None,
        headless=not args.headful,
        to_telegram=args.to_telegram,
        tg_target=args.tg_target,
        tg_session=Path(args.tg_session) if args.tg_session else None,
        tg_keep_files=not args.tg_clean,
        tg_mode=args.tg_mode,
        tg_bot_token=args.tg_bot_token,
    )
    # Friendly hint when cookies are missing entirely.
    if cfg.cookies_file is None:
        logger.warning(
            "No cookies file found. Pass --cookies /path/to/cookies.txt "
            "or set X_COOKIES_FILE. See cookies.txt.example"
        )
    try:
        return run_config(cfg)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
