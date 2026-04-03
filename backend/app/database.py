from __future__ import annotations

"""Async SQLAlchemy engine and session factory."""

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


async def create_tables() -> None:
    """Create all tables (dev convenience — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_startup_migrations)


def _run_startup_migrations(sync_conn) -> None:
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
