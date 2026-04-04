"""Cross-cutting protocols and small utilities with no heavy dependencies."""

from __future__ import annotations

from gisst.core.notifier import Notifier
from gisst.core.text import split_message

__all__ = ["Notifier", "split_message"]
