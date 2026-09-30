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
