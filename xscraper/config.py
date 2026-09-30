"""Shared configuration dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScraperConfig:
    handle: str
    limit: int = 50
    tab: str = "media"  # media | tweets | likes
    only: str = ""  # video | photo | gif | mixed | text | ""
    out: Path | None = None
    dl_dir: Path | None = None
    cookies_file: Path | None = None
    headless: bool = True
    to_telegram: bool = False
    tg_target: str | None = None
    tg_session: Path | None = None
    tg_keep_files: bool = True
    tg_mode: str | None = None
    tg_bot_token: str | None = None

    def __post_init__(self) -> None:
        self.handle = self.handle.lstrip("@")
        self.tab = self.tab.lower()
        self.only = self.only.lower()
        if self.out is None:
            self.out = Path(f"{self.handle}.txt")


@dataclass
class DownloadConfig:
    dl_dir: Path
    template: str = "%(id)s-%(autonumber)s.%(ext)s"
    retries: int = 3
    timeout: int = 600


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    target: str | int  # 'me' | @username | chat id | invite link
    mode: str = "userbot"  # userbot | bot
    bot_token: str | None = None
    session: Path = Path("xscraper.session")
    keep_files: bool = True
    caption_template: str = "[{kind}] @{handle}\n{url}"

    def __post_init__(self) -> None:
        self.mode = self.mode.lower()
        if self.mode not in ("userbot", "bot"):
            raise ValueError("TG mode must be userbot|bot")
        if self.mode == "bot" and not self.bot_token:
            raise ValueError("Bot mode needs TG_BOT_TOKEN.")
