"""Parser for the ``[SAVE_TO_NOTION: {...}]`` marker the agent appends to its
responses.

The agent embeds a JSON object inside the marker; we extract it with a
balanced-brace scan (the summary text can itself contain braces, so a regex
won't do), validate it into a :class:`ResearchFinding`, and strip the marker
from the user-facing text. Faithful port of ``parseNotionMarker`` from the
original ``claude.ts`` with stricter validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from gisst.constants import NOTION_MARKER_TAG
from gisst.logging import get_logger
from gisst.models.research import ResearchFinding

log = get_logger("agent.markers")


@dataclass(slots=True)
class ParsedResponse:
    """Result of stripping a save-marker from agent output."""

    clean_text: str
    finding: ResearchFinding | None = None

    @property
    def has_finding(self) -> bool:
        return self.finding is not None


def _find_balanced_json(text: str, start: int) -> tuple[int, int] | None:
    """Return ``(json_start, json_end)`` for the first balanced ``{...}`` at or
    after ``start``, or ``None`` if no balanced object is found."""
    json_start = text.find("{", start)
    if json_start == -1:
        return None

    depth = 0
    for i in range(json_start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json_start, i + 1
    return None


def parse_notion_marker(text: str) -> ParsedResponse:
    """Extract and validate a ``[SAVE_TO_NOTION: {...}]`` marker from ``text``."""
    start_idx = text.find(NOTION_MARKER_TAG)
    if start_idx == -1:
        return ParsedResponse(clean_text=text)

    bounds = _find_balanced_json(text, start_idx)
    if bounds is None:
        return ParsedResponse(clean_text=text)

    json_start, json_end = bounds
    closing_bracket = text.find("]", json_end)
    marker_end = closing_bracket + 1 if closing_bracket != -1 else json_end
    full_marker = text[start_idx:marker_end]

    try:
        payload = json.loads(text[json_start:json_end])
        finding = ResearchFinding.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("failed to parse SAVE_TO_NOTION marker", error=str(exc))
        return ParsedResponse(clean_text=text)

    clean_text = text.replace(full_marker, "").strip()
    return ParsedResponse(clean_text=clean_text, finding=finding)
