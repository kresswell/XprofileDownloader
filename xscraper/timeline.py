"""Timeline payload parsing. No DOM parsing - only GraphQL JSON sniffing.

X renames its timeline operations regularly, so we sniff every GraphQL
response for tweet entries instead of allowlisting operation names.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

ENTRY_RE = re.compile(r'"entryId"\s*:\s*"tweet-(\d+)"')
REST_ID_RE = re.compile(r'"rest_id"\s*:\s*"(\d+)"')

MEDIA_HINTS = ("photo", "video", "animated_gif")


def extract_ids(payload_text: str) -> list[str]:
    """Pull tweet ids from a timeline JSON payload, timeline order first."""
    ids = ENTRY_RE.findall(payload_text)
    if not ids:
        ids = REST_ID_RE.findall(payload_text)
    return ids


def _walk(node: Any) -> Iterator[Any]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def tweet_entries(payload: dict) -> Iterator[tuple[str, dict]]:
    """Yield (tweet_id, entry_dict) for every tweet entry in a timeline payload."""
    for node in _walk(payload):
        if isinstance(node, dict):
            entry_id = node.get("entryId")
            if isinstance(entry_id, str) and entry_id.startswith("tweet-"):
                yield entry_id.split("-", 1)[1], node


def media_kinds(entry: dict) -> list[str]:
    """Media types attached to one tweet entry: photo / video / animated_gif."""
    kinds: list[str] = []
    for node in _walk(entry):
        if isinstance(node, dict):
            kind = node.get("type")
            if kind in MEDIA_HINTS and ("media_url_https" in node or "video_info" in node):
                if kind not in kinds:
                    kinds.append(kind)
    return kinds


def kind_label(kinds: list[str]) -> str:
    if not kinds:
        return "text"
    if kinds == ["photo"]:
        return "photo"
    if kinds == ["video"]:
        return "video"
    if kinds == ["animated_gif"]:
        return "gif"
    return "mixed"
