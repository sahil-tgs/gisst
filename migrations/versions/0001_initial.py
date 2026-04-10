"""initial schema

Creates every table in the Gisst schema: sessions, schedule_jobs,
staged_findings, findings, digests, and allowed_groups. Mirrors
``gisst.db.models`` exactly (column types, nullability, indexes, and the
deterministic constraint names from the project's naming convention).

Revision ID: 0001
Revises:
Create Date: 2026-04-05 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- sessions -------------------------------------------------------------
    op.create_table(
        "sessions",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_sessions")),
    )

    # -- schedule_jobs --------------------------------------------------------
    op.create_table(
        "schedule_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("cadence", sa.String(length=64), nullable=False),
        sa.Column("digest_time", sa.String(length=16), nullable=False),
        sa.Column("digest_timezone", sa.String(length=64), nullable=False),
        sa.Column("lookback_window", sa.String(length=32), nullable=False),
        sa.Column("platform_priority", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("last_crawl", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_digest", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schedule_jobs")),
    )
    op.create_index(
        op.f("ix_schedule_jobs_chat_id"),
        "schedule_jobs",
        ["chat_id"],
        unique=False,
    )

    # -- staged_findings ------------------------------------------------------
    op.create_table(
        "staged_findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("crawl_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staged_findings")),
    )
    op.create_index(
        op.f("ix_staged_findings_job_id"),
        "staged_findings",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_findings_day"),
        "staged_findings",
        ["day"],
        unique=False,
    )

    # -- findings -------------------------------------------------------------
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("topic", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_findings", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("finding_type", sa.String(length=32), nullable=False),
        sa.Column("researcher", sa.String(length=256), nullable=True),
        sa.Column("notion_page_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_findings")),
    )
    op.create_index(
        op.f("ix_findings_finding_type"),
        "findings",
        ["finding_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_created_at"),
        "findings",
        ["created_at"],
        unique=False,
    )

    # -- digests --------------------------------------------------------------
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.String(length=64), nullable=True),
        sa.Column("notion_page_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_digests")),
    )
    op.create_index(
        op.f("ix_digests_schedule_id"),
        "digests",
        ["schedule_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digests_created_at"),
        "digests",
        ["created_at"],
        unique=False,
    )

    # -- allowed_groups -------------------------------------------------------
    op.create_table(
        "allowed_groups",
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("registered_by", sa.String(length=128), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("chat_id", name=op.f("pk_allowed_groups")),
        sa.UniqueConstraint("chat_id", name="uq_allowed_groups_chat_id"),
    )


def downgrade() -> None:
    op.drop_table("allowed_groups")

    op.drop_index(op.f("ix_digests_created_at"), table_name="digests")
    op.drop_index(op.f("ix_digests_schedule_id"), table_name="digests")
    op.drop_table("digests")

    op.drop_index(op.f("ix_findings_created_at"), table_name="findings")
    op.drop_index(op.f("ix_findings_finding_type"), table_name="findings")
    op.drop_table("findings")

    op.drop_index(op.f("ix_staged_findings_day"), table_name="staged_findings")
    op.drop_index(op.f("ix_staged_findings_job_id"), table_name="staged_findings")
    op.drop_table("staged_findings")

    op.drop_index(op.f("ix_schedule_jobs_chat_id"), table_name="schedule_jobs")
    op.drop_table("schedule_jobs")

    op.drop_table("sessions")
