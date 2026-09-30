"""Local-disk storage via yt-dlp."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger

from xscraper.config import DownloadConfig
from xscraper.scraper import Post
from xscraper.storage.base import StorageResult


DOWNLOADABLE = ("video", "gif", "photo", "mixed")


class LocalStorage:
    def __init__(self, config: DownloadConfig) -> None:
        self.config = config
        if shutil.which("yt-dlp") is None:
            raise RuntimeError("yt-dlp not found on PATH. Install it to download media.")

    def download_one(self, url: str) -> bool:
        cmd = [
            "yt-dlp",
            "--no-overwrites",
            "--retries",
            str(self.config.retries),
            "-P",
            str(self.config.dl_dir),
            "-o",
            self.config.template,
            url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.timeout)
        except subprocess.TimeoutExpired:
            logger.warning(f"TIMEOUT {url}")
            return False
        if result.returncode != 0:
            err = (result.stderr or "").strip().splitlines()
            logger.warning(f"FAILED {url} :: {err[-1] if err else 'yt-dlp error'}")
            return False
        return True

    def store(self, posts: list[Post]) -> StorageResult:
        self.config.dl_dir.mkdir(parents=True, exist_ok=True)
        queue = [p for p in posts if p.kind in DOWNLOADABLE]
        result = StorageResult(skipped=len(posts) - len(queue))
        if result.skipped:
            logger.info(f"Skipping {result.skipped} text/unknown post(s): nothing to download.")
        for i, post in enumerate(queue, 1):
            logger.info(f"[{i}/{len(queue)}] {post.url}")
            if self.download_one(post.url):
                result.ok += 1
            else:
                result.failed += 1
        return result


def default_dl_dir(handle: str, dl_arg: str) -> Path | None:
    """Legacy helper: '' -> None, 'download' -> <handle>_downloads, else path."""
    if not dl_arg:
        return None
    if dl_arg == "download":
        return Path(f"{handle}_downloads")
    return Path(dl_arg)
