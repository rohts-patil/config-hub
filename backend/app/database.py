from __future__ import annotations

"""Async SQLAlchemy engine and session factory."""

import asyncio
from pathlib import Path
import secrets

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    ),
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def run_database_migrations() -> None:
    """Apply Alembic migrations, bootstrapping older local databases when needed."""
    async with engine.begin() as conn:
        state = await conn.run_sync(_inspect_database_state)
        if state["has_app_tables"] and not state["has_alembic_version"]:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_bootstrap_legacy_schema)
            await asyncio.to_thread(_run_alembic_command, "stamp", "head")
            return

    await asyncio.to_thread(_run_alembic_command, "upgrade", "head")


def _run_alembic_command(command_name: str, revision: str) -> None:
    config = AlembicConfig(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "alembic"),
    )
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    getattr(command, command_name)(config, revision)


def _inspect_database_state(sync_conn) -> dict[str, bool]:
    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    app_tables = set(Base.metadata.tables.keys())
    return {
        "has_app_tables": bool(table_names & app_tables),
        "has_alembic_version": "alembic_version" in table_names,
    }


def _bootstrap_legacy_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "google_sub" not in user_columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)"))
        sync_conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_sub "
                "ON users (google_sub)"
            )
        )

    if inspector.has_table("audit_logs"):
        audit_columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }
        if "product_id" not in audit_columns:
            sync_conn.execute(text("ALTER TABLE audit_logs ADD COLUMN product_id VARCHAR(36)"))
        sync_conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_product_id "
                "ON audit_logs (product_id)"
            )
        )

    if inspector.has_table("organization_invites"):
        invite_columns = {
            column["name"] for column in inspector.get_columns("organization_invites")
        }
        if "token" not in invite_columns:
            sync_conn.execute(
                text(
                    "ALTER TABLE organization_invites "
                    "ADD COLUMN token VARCHAR(255)"
                )
            )
        missing_invite_tokens = sync_conn.execute(
            text("SELECT id FROM organization_invites WHERE token IS NULL")
        ).fetchall()
        for row in missing_invite_tokens:
            sync_conn.execute(
                text(
                    "UPDATE organization_invites "
                    "SET token = :token "
                    "WHERE id = :invite_id"
                ),
                {"token": secrets.token_urlsafe(32), "invite_id": row.id},
            )
        sync_conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_organization_invites_token "
                "ON organization_invites (token)"
            )
        )
        if "email_sent_at" not in invite_columns:
            sync_conn.execute(
                text(
                    "ALTER TABLE organization_invites "
                    "ADD COLUMN email_sent_at DATETIME"
                )
            )

    if inspector.has_table("webhooks"):
        webhook_columns = {column["name"] for column in inspector.get_columns("webhooks")}
        if "signing_secret" not in webhook_columns:
            sync_conn.execute(
                text("ALTER TABLE webhooks ADD COLUMN signing_secret VARCHAR(255)")
            )
        missing_signing_secrets = sync_conn.execute(
            text("SELECT id FROM webhooks WHERE signing_secret IS NULL")
        ).fetchall()
        for row in missing_signing_secrets:
            sync_conn.execute(
                text(
                    "UPDATE webhooks "
                    "SET signing_secret = :signing_secret "
                    "WHERE id = :webhook_id"
                ),
                {
                    "signing_secret": secrets.token_urlsafe(32),
                    "webhook_id": row.id,
                },
            )
        if "last_email_error" not in invite_columns:
            sync_conn.execute(
                text(
                    "ALTER TABLE organization_invites "
                    "ADD COLUMN last_email_error TEXT"
                )
            )
