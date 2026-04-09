"""``parse_notion_marker`` behaviour: no marker passes through, a valid marker is
parsed and stripped (even with braces inside the summary), malformed JSON is left
untouched, and the camelCase ``keyFindings`` alias maps to ``key_findings``."""

from __future__ import annotations

from gisst.agent.markers import parse_notion_marker


def test_no_marker_returns_input_unchanged() -> None:
    text = "Here is a plain answer with no marker at all."
    parsed = parse_notion_marker(text)
    assert parsed.clean_text == text
    assert parsed.finding is None
    assert parsed.has_finding is False


def test_valid_marker_is_parsed_and_stripped() -> None:
    text = (
        "Here are the findings.\n\n"
        '[SAVE_TO_NOTION: {"title": "AI News", "topic": "AI", '
        '"summary": "Two sentences.", "keyFindings": ["a", "b"], '
        '"sources": [{"title": "Src", "url": "https://e.com"}], "tags": ["ai"]}]'
    )
    parsed = parse_notion_marker(text)
    assert parsed.finding is not None
    assert parsed.finding.title == "AI News"
    assert parsed.finding.topic == "AI"
    # Marker must be gone from the user-facing text.
    assert "SAVE_TO_NOTION" not in parsed.clean_text
    assert parsed.clean_text == "Here are the findings."


def test_marker_with_braces_inside_summary() -> None:
    # The summary itself contains braces; a regex would mis-balance, the
    # balanced-brace scan must not.
    text = (
        "Reply body.\n"
        '[SAVE_TO_NOTION: {"title": "Config", '
        '"summary": "The object {a: 1} nests {deeper: {x}}.", '
        '"keyFindings": ["uses {braces}"]}]'
    )
    parsed = parse_notion_marker(text)
    assert parsed.finding is not None
    assert parsed.finding.title == "Config"
    assert parsed.finding.summary == "The object {a: 1} nests {deeper: {x}}."
    assert parsed.finding.key_findings == ["uses {braces}"]
    assert "SAVE_TO_NOTION" not in parsed.clean_text
    assert parsed.clean_text == "Reply body."


def test_malformed_json_leaves_text_untouched() -> None:
    text = 'Answer.\n[SAVE_TO_NOTION: {"title": "broken", bad json here}]'
    parsed = parse_notion_marker(text)
    assert parsed.finding is None
    # On parse failure the original text (marker included) is returned verbatim.
    assert parsed.clean_text == text


def test_missing_required_title_is_treated_as_invalid() -> None:
    # ``title`` is required on ResearchFinding; a payload without it must fail
    # validation and leave the text untouched.
    text = 'Body.\n[SAVE_TO_NOTION: {"topic": "no title here"}]'
    parsed = parse_notion_marker(text)
    assert parsed.finding is None
    assert parsed.clean_text == text


def test_camelcase_keyfindings_maps_to_snake_case() -> None:
    text = '[SAVE_TO_NOTION: {"title": "X", "keyFindings": ["one", "two", "three"]}]'
    parsed = parse_notion_marker(text)
    assert parsed.finding is not None
    assert parsed.finding.key_findings == ["one", "two", "three"]
