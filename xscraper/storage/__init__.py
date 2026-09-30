"""Storage backends. Implement MediaStorage to add new destinations."""
from __future__ import annotations

from xscraper.storage.base import MediaStorage, StorageResult
from xscraper.storage.local import LocalStorage
from xscraper.storage.telegram import TelegramStorage, telegram_config_from_env

__all__ = ["MediaStorage", "StorageResult", "LocalStorage", "TelegramStorage", "telegram_config_from_env"]

