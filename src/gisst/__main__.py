"""``python -m gisst`` entrypoint.

Runs the full application (Telegram bot + scheduler + API dashboard) until
interrupted with Ctrl-C / SIGTERM.
"""

from __future__ import annotations

import asyncio

from gisst.app import run


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        print("\nGisst stopped.")


if __name__ == "__main__":
    main()
