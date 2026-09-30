# XProfileDownloader

Modular X/Twitter profile scraper. Collects canonical post links (`https://x.com/i/status/<id>`) by sniffing the page's own GraphQL JSON in a real browser — no DOM parsing — then downloads media locally with `yt-dlp` and optionally uploads to Telegram (userbot or bot) via Telethon.

New backends plug in via `xscraper/storage/base.py` (`MediaStorage` protocol).

## Layout

```
main.py                  # entrypoint
test_telegram.py         # Telegram login/upload smoke test (no scraping)
xscraper/
  config.py              # ScraperConfig, DownloadConfig, TelegramConfig
  env.py                 # .env loader (real env always wins)
  cookies.py             # Netscape cookies.txt loading
  timeline.py            # GraphQL payload parsing, kind labels
  scraper.py             # XProfileScraper.collect() -> list[Post]
  storage/
    base.py              # MediaStorage protocol
    local.py             # LocalStorage via yt-dlp
    telegram.py          # TelegramStorage via Telethon (userbot + bot)
  cli.py                 # argparse CLI
.env.example             # copy to .env, never commit .env
cookies.txt.example
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
# yt-dlp as a binary:
pip install yt-dlp
cp .env.example .env
chmod 600 .env cookies.txt
```

## .env (all credentials)

All secrets live in `.env` (gitignored), never in code. Real environment vars override `.env`.

```bash
# X cookies (alternative to --cookies)
X_COOKIES_FILE=./cookies.txt

# Telegram mode: userbot | bot
TG_MODE=userbot
# Both modes need these (https://my.telegram.org):
TG_API_ID=
TG_API_HASH=
# Userbot session (file <name>.session, gitignored). First run asks phone+code.
TG_SESSION=xscraper
# Bot mode only (from @BotFather):
TG_BOT_TOKEN=
# Destination: 'me' (userbot Saved Messages), @username, chat id, invite link.
# Bots cannot use 'me' — use a chat/channel id where the bot is member/admin.
TG_TARGET=me
```

## Cookies (required for X)

Cookies stay on your PC, never in code.

1. Log into x.com in Chrome/Firefox.
2. Export with "Get cookies.txt LOCALLY" extension.
3. Save as `./cookies.txt` (`chmod 600 cookies.txt`).

Priority: `--cookies <path>` > `$X_COOKIES_FILE` (or `.env`) > `./cookies.txt`.

## Usage

```
python main.py handle [limit] [tab] [out] [only] [dl_dir]
  [--cookies PATH] [--headful]
  [--to-telegram] [--tg-mode userbot|bot] [--tg-target T]
  [--tg-session S] [--tg-bot-token TOK] [--tg-clean] [--env-file PATH]
```

- `handle`: without `@`, e.g. `elonmusk`
- `limit`: max links (default 50)
- `tab`: `media` (default) or `tweets`
- `out`: txt export (default `<handle>.txt`)
- `only`: `video | photo | gif | mixed | text`
- `dl_dir`: folder, or `download` for `<handle>_downloads`
- `--tg-clean`: delete local files after Telegram upload

### Examples with Elon

```bash
# 1. Just collect 50 media post links from @elonmusk
python main.py elonmusk --cookies ./cookies.txt

# 2. Collect 100, export to elon.txt
python main.py elonmusk 100 media elon.txt --cookies ./cookies.txt

# 3. Download videos only from @elonmusk
python main.py elonmusk 50 media elon.txt video download --cookies ./cookies.txt

# 4. Download all media to a custom folder
python main.py elonmusk 100 media elon.txt "" ./elon_media --cookies ./cookies.txt

# 5. Using .env instead of flags (X_COOKIES_FILE=./cookies.txt in .env)
python main.py elonmusk 50 media elon.txt "" download
```

## Telegram upload (userbot + bot)

Needs `TG_API_ID`/`TG_API_HASH` in `.env`. Userbot first run asks for phone + code, then reuses `<session>.session`.

```bash
# Test connection first (no scraping):
python test_telegram.py --target me
python test_telegram.py --mode bot --target -1001234567890
python test_telegram.py --target me --file ./elon_media/some.mp4

# Scrape Elon + upload to Saved Messages (userbot, .env: TG_MODE=userbot TG_TARGET=me)
python main.py elonmusk 5 media elon.txt video download --to-telegram

# Scrape Elon + upload to channel via bot (.env: TG_MODE=bot + TG_BOT_TOKEN)
python main.py elonmusk 5 media elon.txt video download --to-telegram --tg-mode bot --tg-target -1001234567890

# Upload without keeping local files:
python main.py elonmusk 5 media elon.txt video download --to-telegram --tg-clean
```

Bot notes: create via @BotFather, add it to the target chat/channel as admin (for channels) or member, use the numeric chat id — `me` only works for userbots.

## Adding another storage backend

Implement `MediaStorage` in e.g. `xscraper/storage/s3.py`:

```python
from xscraper.storage.base import StorageResult
class S3Storage:
    def store(self, posts) -> StorageResult: ...
```

then call it from `cli.py` / your own script instead of `LocalStorage`.

## Troubleshooting

- `Hit a login wall / block page` → cookies expired or IP flagged. Export fresh `cookies.txt` and retry.
- `No posts found` → private/suspended/nonexistent handle, or rate-limited.
- `yt-dlp not found` → install it and ensure it's on `PATH`.
- `Set TG_API_ID...` → fill `.env` (see `.env.example`).
- `Bots cannot use target 'me'` → use a chat id where the bot is a member.
