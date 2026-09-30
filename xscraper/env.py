"""Load .env into os.environ. Real environment always wins over .env values."""
from __future__ import annotations

from pathlib import Path


def load_env(dotenv_path: str | Path | None = None) -> Path | None:
    """Load .env (explicit path > ./.env). Returns path used, or None."""
    candidates: list[Path] = []
    if dotenv_path:
        candidates.append(Path(dotenv_path).expanduser())
    candidates.append(Path(".env"))
    for p in candidates:
        if p.is_file():
            _load_file(p)
            return p
    return None


def _load_file(p: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(p, override=False)
        return
    except ImportError:
        pass
    # Minimal fallback parser (KEY=VAL, ignores # comments, strips quotes).
    import os

    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val
