"""Storage interface. Future backends (Telegram, S3, ...) implement this."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from xscraper.scraper import Post


@dataclass
class StorageResult:
    ok: int = 0
    failed: int = 0
    skipped: int = 0


class MediaStorage(Protocol):
    """Any destination for scraped media must implement store()."""

    def store(self, posts: list[Post]) -> StorageResult:
        ...
