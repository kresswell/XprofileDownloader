"""Storage backends. Implement MediaStorage to add new destinations."""
from __future__ import annotations

from xscraper.storage.base import MediaStorage, StorageResult
from xscraper.storage.local import LocalStorage

__all__ = ["MediaStorage", "StorageResult", "LocalStorage"]
