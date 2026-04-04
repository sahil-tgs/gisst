"""Native Anthropic SDK runtime.

For deployments without the Claude Code CLI installed, this backend runs a
server-side tool-use loop directly against the Messages API. The only tool it
exposes is Anthropic's hosted web search (``web_search_20250305``), which runs
on Anthropic's infrastructure - there is nothing to execute client-side. We
just keep re-sending the accumulated transcript until the model stops asking to
search (``stop_reason`` becomes ``end_turn``) or we hit the configured turn cap.

This runtime is stateless with respect to GISST's session persistence: it never
resumes prior context across calls. When no ``session_id`` is supplied it mints
a fresh uuid4 so the layer above still gets a stable handle to record.

The ``anthropic`` package is imported lazily so this module imports cleanly even
when the SDK isn't installed (the CLI backend is the default).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

from gisst.agent.runtime.base import AgentRequest, AgentResult, RuntimeError_
from gisst.config import Settings
from gisst.logging import get_logger

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

log = get_logger("agent.runtime.api")

# Hosted web search tool. The basic variant is broadly available; ``max_uses``
# bounds how many searches Claude may run within a single turn.
_WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

# Generous output ceiling; the API runs the search loop server-side and we read
# the final message back each turn.
_MAX_TOKENS = 8192


class AnthropicApiRuntime:
    """Run one agent turn via the Anthropic Messages API tool-use loop."""

    name = "api"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncAnthropic | None = None

    def _ensure_client(self) -> AsyncAnthropic:
        """Lazily construct the SDK client, validating the API key."""
        if self._client is not None:
            return self._client

        api_key = self._settings.agent.anthropic_api_key
        if not api_key:
            raise RuntimeError_("AnthropicApiRuntime requires ANTHROPIC_API_KEY to be set")

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise RuntimeError_("the 'anthropic' package is required for the api backend") from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    @staticmethod
    def _collect_text(content: list[Any]) -> str:
        """Concatenate the text blocks of one assistant message."""
        parts: list[str] = []
        for block in content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)

    async def run(self, request: AgentRequest) -> AgentResult:
        """Drive the server-side web-search loop to a final answer."""
        client = self._ensure_client()
        model = self._settings.agent.model
        max_turns = max(1, self._settings.agent.max_turns)

        messages: list[dict[str, Any]] = [{"role": "user", "content": request.prompt}]
        text_parts: list[str] = []
        turns = 0

        for turns in range(1, max_turns + 1):
            try:
                response = await client.messages.create(
                    model=model,
                    max_tokens=_MAX_TOKENS,
                    system=request.system_prompt,
                    tools=cast(Any, [_WEB_SEARCH_TOOL]),
                    messages=cast(Any, messages),
                )
            except Exception as exc:
                log.error("api.request_failed", turn=turns, error=str(exc))
                raise RuntimeError_(f"Anthropic API call failed: {exc}") from exc

            turn_text = self._collect_text(response.content)
            if turn_text:
                text_parts.append(turn_text)

            # web_search is executed server-side and its results are already
            # embedded in ``response.content``. We just echo the assistant
            # message back so the model can continue from where it paused.
            if response.stop_reason in ("tool_use", "pause_turn"):
                messages.append({"role": "assistant", "content": response.content})
                continue

            # end_turn (or any terminal reason like max_tokens): we're done.
            break
        else:
            log.warning("api.max_turns_reached", turns=max_turns)

        text = "\n".join(part for part in text_parts if part).strip()
        if not text:
            raise RuntimeError_("Anthropic API returned no text content")

        session_id = request.session_id or str(uuid.uuid4())
        return AgentResult(
            text=text,
            session_id=session_id,
            backend=self.name,
            turns=turns,
        )
