"""Claude Code CLI runtime.

Shells out to the ``claude`` binary (``claude -p``), the same backend the
TypeScript prototype used. Sessions are resumed via ``--resume`` and the CLI
itself owns session creation, persistence, native WebSearch/WebFetch, and file
tools. Marker parsing and Notion sync happen above this layer, so the runtime's
sole job is "send the prompt, return the text + resolved session id".

Interactive turns use ``--output-format json`` so we can read the
``session_id`` back; headless Watchout crawl/digest jobs use
``--output-format text`` and carry their full prompt in the message (no system
prompt, no session).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from gisst.agent.runtime.base import AgentRequest, AgentResult, RuntimeError_
from gisst.config import Settings
from gisst.logging import get_logger

log = get_logger("agent.runtime.cli")

# ``bun`` (and other user-level tooling the CLI may shell out to) commonly lives
# under ~/.bun/bin; adding it to PATH is harmless when the directory is absent.
_BUN_BIN = Path.home() / ".bun" / "bin"


class ClaudeCliRuntime:
    """Run one agent turn by invoking the Claude Code CLI."""

    name = "cli"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_argv(self, request: AgentRequest) -> list[str]:
        """Assemble the ``claude`` command line for this request."""
        output_format = "text" if request.headless else "json"
        argv = [
            "claude",
            "-p",
            request.prompt,
            "--output-format",
            output_format,
            "--model",
            self._settings.agent.model,
            "--dangerously-skip-permissions",
        ]
        # Headless crawl/digest calls have no system prompt - the prompt *is*
        # the message. Only interactive turns carry a system prompt and resume.
        if not request.headless:
            argv += ["--system-prompt", request.system_prompt]
        if request.session_id:
            argv += ["--resume", request.session_id]
        return argv

    def _build_env(self) -> dict[str, str]:
        """Copy the environment with ~/.bun/bin prepended to PATH."""
        env = dict(os.environ)
        path = env.get("PATH", "")
        bun = str(_BUN_BIN)
        if bun not in path.split(os.pathsep):
            env["PATH"] = f"{bun}{os.pathsep}{path}" if path else bun
        return env

    async def run(self, request: AgentRequest) -> AgentResult:
        """Execute the CLI, enforce the timeout, and parse its output."""
        argv = self._build_argv(request)
        timeout = self._settings.agent.timeout_seconds
        cwd = str(self._settings.work_dir)

        log.debug(
            "cli.spawn",
            headless=request.headless,
            resume=bool(request.session_id),
            model=self._settings.agent.model,
        )

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=self._build_env(),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError as exc:
            proc.kill()
            # Reap the killed process so it doesn't linger as a zombie.
            await proc.wait()
            log.warning("cli.timeout", timeout=timeout)
            raise RuntimeError_(f"claude CLI timed out after {timeout}s") from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0 and not stdout:
            log.error("cli.nonzero_exit", code=proc.returncode, stderr=stderr[:500])
            raise RuntimeError_(f"claude CLI exited {proc.returncode}: {stderr or '<no output>'}")

        if request.headless:
            # Text output: the result is the raw stdout.
            return AgentResult(
                text=stdout,
                session_id=None,
                backend=self.name,
                turns=1,
            )

        # JSON output: pull session_id + result; fall back to raw text on a
        # malformed payload so a partial answer is never silently dropped.
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            log.warning("cli.json_parse_failed", preview=stdout[:200])
            return AgentResult(
                text=stdout,
                session_id=request.session_id,
                backend=self.name,
                turns=1,
            )

        session_id = data.get("session_id") or request.session_id
        text = data.get("result")
        if text is None:
            text = stdout
        return AgentResult(
            text=str(text),
            session_id=session_id,
            backend=self.name,
            turns=1,
        )
