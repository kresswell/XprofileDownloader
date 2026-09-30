# XProfileDownloader

Modular X/Twitter profile scraper. Collects canonical post links (`https://x.com/i/status/<id>`) by sniffing the page's own GraphQL JSON in a real browser — no DOM parsing — then downloads media locally with `yt-dlp`.

Future storage backends (Telegram, S3, ...) plug in via `xscraper/storage/base.py`.

## Layout

```
main.py                  # entrypoint
xscraper/
  config.py              # ScraperConfig, DownloadConfig
  cookies.py             # Netscape cookies.txt loading
  timeline.py            # GraphQL payload parsing, kind labels
  scraper.py             # XProfileScraper.collect() -> list[Post]
  storage/
    base.py              # MediaStorage protocol
    local.py             # LocalStorage via yt-dlp
  cli.py                 # argparse CLI
cookies.txt.example
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
# yt-dlp as a binary:
pip install yt-dlp
```

## Cookies (required)

Cookies stay on your PC, never in code.

1. Log into x.com in Chrome/Firefox.
2. Export with "Get cookies.txt LOCALLY" extension.
3. Save as `./cookies.txt`:
```bash
chmod 600 cookies.txt
```

The loader checks in order: `--cookies <path>` > `$X_COOKIES_FILE` > `./cookies.txt`.

## Usage

```
python main.py handle [limit] [tab] [out] [only] [dl_dir] [--cookies PATH] [--headful]
```

- `handle`: without `@`, e.g. `elonmusk`
- `limit`: max links (default 50)
- `tab`: `media` (default) or `tweets`
- `out`: txt export (default `<handle>.txt`)
- `only`: `video | photo | gif | mixed | text`
- `dl_dir`: folder, or `download` for `<handle>_downloads`

### Examples with Elon

```bash
# 1. Just collect 50 media post links from @elonmusk
python main.py elonmusk --cookies ./cookies.txt

# 2. Collect 100, export to elon.txt
python main.py elonmusk 100 media elon.txt --cookies ./cookies.txt

# 3. Download videos only from @elonmusk
python main.py elonmusk 50 media elon.txt video download --cookies ./cookies.txt

# 4. Download all media (video/photo/gif) to a custom folder
python main.py elonmusk 100 media elon.txt "" ./elon_media --cookies ./cookies.txt

# 5. Using env var instead of --cookies
export X_COOKIES_FILE=~/cookies.txt
python main.py elonmusk 50 media elon.txt "" download
```

## Adding Telegram / other storage

Implement `MediaStorage` in e.g. `xscraper/storage/telegram.py`:

```python
from xscraper.storage.base import StorageResult
class TelegramStorage:
    def store(self, posts) -> StorageResult: ...
```

then call it from `cli.py` / your own script instead of `LocalStorage`.

## Troubleshooting

- `Hit a login wall / block page` → cookies expired or IP flagged. Export fresh `cookies.txt` and retry.
- `No posts found` → private/suspended/nonexistent handle, or rate-limited.
- `yt-dlp not found` → install it and ensure it's on `PATH`.
