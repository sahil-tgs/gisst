"""``split_message`` behaviour: short text passes through untouched, long text is
chunked under the limit, paragraph boundaries are preferred, and the content
round-trips (modulo the whitespace the splitter strips at chunk seams)."""

from __future__ import annotations

from gisst.constants import TELEGRAM_SPLIT_TARGET
from gisst.core.text import split_message


def test_short_text_is_single_chunk() -> None:
    text = "just a short line"
    chunks = split_message(text)
    assert chunks == [text]


def test_text_exactly_at_limit_is_single_chunk() -> None:
    text = "a" * TELEGRAM_SPLIT_TARGET
    assert split_message(text) == [text]


def test_long_text_splits_into_multiple_bounded_chunks() -> None:
    max_length = 100
    text = "word " * 500  # 2500 chars, no paragraph breaks
    chunks = split_message(text, max_length=max_length)
    assert len(chunks) > 1
    assert all(len(chunk) <= max_length for chunk in chunks)


def test_splits_on_paragraph_boundary_when_possible() -> None:
    max_length = 50
    para_a = "A" * 40
    para_b = "B" * 40
    text = f"{para_a}\n\n{para_b}"
    chunks = split_message(text, max_length=max_length)
    # The cleanest split is the blank-line boundary, giving the two paragraphs
    # as separate, intact chunks.
    assert chunks[0] == para_a
    assert para_b in chunks[-1]


def test_rejoining_preserves_content_modulo_whitespace() -> None:
    max_length = 80
    text = "\n\n".join(f"Paragraph {i} " + ("x" * 60) for i in range(10))
    chunks = split_message(text, max_length=max_length)

    # Stripping seam whitespace on both sides, the concatenation of the chunks
    # must reproduce the original stripped content.
    rejoined = "".join(chunks)
    assert rejoined.replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")


def test_hard_cut_when_no_natural_boundary() -> None:
    max_length = 30
    text = "x" * 200  # no spaces or newlines anywhere
    chunks = split_message(text, max_length=max_length)
    assert all(len(chunk) <= max_length for chunk in chunks)
    assert "".join(chunks) == text
