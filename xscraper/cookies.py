"""Cookie loading. Cookies never live in code - only in a local file."""
from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


def parse_netscape_cookies(text: str) -> list[dict]:
    """Parse Netscape-format cookie file text into playwright cookie dicts."""
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts = line.split()
        if len(parts) < 7:
            continue
        domain, _, path, _, _, name, value = parts[:7]
        cookies.append({"name": name, "value": value, "domain": domain, "path": path})
    return cookies


def resolve_cookies_file(cli_arg: str | Path | None = None) -> Path | None:
    """Priority: CLI arg > X_COOKIES_FILE env > ./cookies.txt.

    Returns None if nothing exists (caller decides whether auth is required).
    """
    candidates: list[Path] = []
    if cli_arg:
        candidates.append(Path(cli_arg).expanduser())
    env = os.environ.get("X_COOKIES_FILE", "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(Path("cookies.txt"))
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_cookies(path: str | Path) -> list[dict]:
    """Load and parse a Netscape cookie file. Warns on loose permissions."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Cookies file not found: {p}")
    try:
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            logger.warning(
                f"Cookies file {p} is readable by others (mode {oct(mode)}). "
                "Run: chmod 600 " + str(p)
            )
    except OSError:
        pass
    text = p.read_text(encoding="utf-8", errors="ignore")
    cookies = parse_netscape_cookies(text)
    if not cookies:
        raise ValueError(f"No cookies parsed from {p}. Is it Netscape format?")
    logger.info(f"Loaded {len(cookies)} cookies from {p}")
    return cookies
