"""Project-wide constants and magic strings.

Keeping these in one place means the prompt engine, the marker parser, and the
Notion sync layer all agree on the exact same tokens.
"""

from __future__ import annotations

from typing import Final

# Marker the agent appends to its output when a finding should be persisted to
# the Notion knowledge base. Parsed by `gisst.agent.markers`.
NOTION_MARKER_TAG: Final[str] = "[SAVE_TO_NOTION:"

# Telegram hard limit on a single message body.
TELEGRAM_MAX_MESSAGE_LEN: Final[int] = 4096

# Practical split target - leave headroom under the hard limit for entities.
TELEGRAM_SPLIT_TARGET: Final[int] = 4000

# Notion rich-text properties cap out at 2000 characters per text object.
NOTION_TEXT_LIMIT: Final[int] = 2000

# The identifier of the single default agent profile (multi-agent support is
# scaffolded but the prototype ships one profile).
DEFAULT_PROFILE_ID: Final[str] = "default"

# Default research persona name.
DEFAULT_AGENT_NAME: Final[str] = "Scout"

# Notion "Type" select values used to classify rows in the Research database.
NOTION_TYPE_RESEARCH: Final[str] = "Research"
NOTION_TYPE_CRAWL: Final[str] = "Crawl"
NOTION_TYPE_DIGEST: Final[str] = "Digest"
