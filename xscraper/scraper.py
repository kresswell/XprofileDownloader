"""Browser scraper: collects canonical post links for a profile."""
from __future__ import annotations

import json
from dataclasses import dataclass

from loguru import logger
from playwright.sync_api import sync_playwright

from xscraper.timeline import extract_ids, kind_label, media_kinds, tweet_entries


@dataclass
class Post:
    url: str
    kind: str  # video | photo | gif | mixed | text | unknown
    tweet_id: str


class XProfileScraper:
    """Opens a profile in Chromium, sniffs GraphQL timeline JSON, returns posts."""

    def __init__(self, cookies: list[dict] | None = None, headless: bool = True) -> None:
        self.cookies = cookies or []
        self.headless = headless

    def profile_url(self, handle: str, tab: str) -> str:
        handle = handle.lstrip("@")
        if tab in ("media", "likes"):
            return f"https://x.com/{handle}/{tab}"
        return f"https://x.com/{handle}"

    def collect(self, handle: str, limit: int = 50, tab: str = "media") -> list[Post]:
        handle = handle.lstrip("@")
        url = self.profile_url(handle, tab)
        logger.info(f"Opening {url}")

        found: list[Post] = []
        seen: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 900},
            )
            if self.cookies:
                context.add_cookies(self.cookies)
            page = context.new_page()

            def on_response(resp) -> None:
                try:
                    if "/graphql/" not in resp.url:
                        return
                    text = resp.text()
                except Exception:
                    return
                if "tweet-" not in text:
                    return
                try:
                    payload = json.loads(text)
                except Exception:
                    payload = None
                if payload is not None:
                    items = [
                        (tid, kind_label(media_kinds(entry)))
                        for tid, entry in tweet_entries(payload)
                    ]
                else:  # non-JSON payload: ids without classification
                    items = [(tid, "unknown") for tid in extract_ids(text)]
                for tid, kind in items:
                    if tid not in seen:
                        seen.add(tid)
                        found.append(
                            Post(
                                url=f"https://x.com/i/status/{tid}",
                                kind=kind,
                                tweet_id=tid,
                            )
                        )

            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)


            for i in range(12):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                page.wait_for_timeout(2000)
                if i % 3 == 2:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                if found:
                    break

            if not found:
                try:
                    page.wait_for_selector("article[data-testid='tweet']", timeout=10000)
                except Exception:
                    text = (page.inner_text("body") or "")[:500]
                    browser.close()
                    if "Log in to X" in text or "Something went wrong" in text:
                        raise RuntimeError(
                            "Hit a login wall / block page: cookies are expired or "
                            "this IP is flagged. Export fresh cookies and retry. "
                            f"Page said: {text[:200]}"
                        )
                    raise RuntimeError(
                        f"No posts found for @{handle} "
                        "(private/suspended/nonexistent, or rate-limited)."
                    )

            stalled = 0
            while len(found) < limit and stalled < 4:
                before = len(found)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                stalled = stalled + 1 if len(found) == before else 0
                logger.info(f"collected {len(found)}/{limit}...")

            browser.close()

        return found[:limit]
