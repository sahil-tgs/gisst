"""Text utilities shared by channel adapters.

``split_message`` mirrors the original TypeScript splitter: it breaks a long
string at the friendliest boundary it can find under ``max_length`` - preferring
paragraph breaks, then line breaks, then spaces, and only hard-cutting as a last
resort.
"""

from __future__ import annotations

from gisst.constants import TELEGRAM_SPLIT_TARGET


def split_message(text: str, max_length: int = TELEGRAM_SPLIT_TARGET) -> list[str]:
    """Split ``text`` into chunks no longer than ``max_length`` characters."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text
    half = max_length // 2

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Prefer a paragraph break, then a line break, then a space.
        split_idx = remaining.rfind("\n\n", 0, max_length)
        if split_idx == -1 or split_idx < half:
            split_idx = remaining.rfind("\n", 0, max_length)
        if split_idx == -1 or split_idx < half:
            split_idx = remaining.rfind(" ", 0, max_length)
        if split_idx == -1 or split_idx < half:
            split_idx = max_length

        chunks.append(remaining[:split_idx])
        remaining = remaining[split_idx:].lstrip()

    return chunks
