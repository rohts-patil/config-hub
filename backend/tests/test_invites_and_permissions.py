from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models import config as _config  # noqa: E402,F401
from app.models import environment as _environment  # noqa: E402,F401
from app.models import organization as _organization  # noqa: E402,F401
from app.models import permission as _permission  # noqa: E402,F401
from app.models import product as _product  # noqa: E402,F401
from app.models import segment as _segment  # noqa: E402,F401
from app.models import setting as _setting  # noqa: E402,F401
from app.models import targeting as _targeting  # noqa: E402,F401
from app.models import user as _user  # noqa: E402,F401
from app.database import Base  # noqa: E402
from app.models.organization import Organization, OrganizationInvite, OrganizationMember, OrgRole  # noqa: E402
from app.models.permission import PermissionGroup  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.auth import register  # noqa: E402
from app.routers.organizations import delete_member  # noqa: E402
from app.routers.permissions import PermissionGroupCreate, create_permission_group  # noqa: E402
from app.schemas.schemas import UserRegister  # noqa: E402


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_register_accepts_pending_org_invite(db_session: AsyncSession):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()

    invite = OrganizationInvite(
        organization_id=org.id,
        email="future@example.com",
        role=OrgRole.MEMBER,
    )
    db_session.add(invite)
    await db_session.flush()

    response = await register(
        UserRegister(
            email="Future@Example.com",
            name="Future User",
            password="supersecurepassword",
        ),
        db=db_session,
    )

    result = await db_session.execute(
        select(User).where(User.email == "future@example.com")
    )
    user = result.scalar_one()

    membership_result = await db_session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()

    remaining_invites = await db_session.execute(select(OrganizationInvite))
    assert response.access_token
    assert membership is not None
    assert membership.role == OrgRole.MEMBER
    assert remaining_invites.scalars().all() == []


@pytest.mark.asyncio
async def test_delete_member_rejects_last_admin(db_session: AsyncSession):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, org])
    await db_session.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    db_session.add(membership)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await delete_member(
            org.id,
            membership.id,
            db=db_session,
            current_user=admin,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Organizations must always have at least one admin"


@pytest.mark.asyncio
async def test_create_permission_group_persists_permissions(db_session: AsyncSession):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, org])
    await db_session.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    product = Product(
        organization_id=org.id,
        name="Checkout",
        description="Main product",
    )
    db_session.add_all([membership, product])
    await db_session.flush()

    group = await create_permission_group(
        product.id,
        PermissionGroupCreate(
            name="Release Managers",
            permissions={
                "canManageFlags": True,
                "canManageSdkKeys": True,
                "canManageWebhooks": False,
            },
        ),
        db=db_session,
        current_user=admin,
    )

    result = await db_session.execute(
        select(PermissionGroup).where(PermissionGroup.id == group.id)
    )
    saved_group = result.scalar_one()

    assert saved_group.name == "Release Managers"
    assert saved_group.permissions["canManageFlags"] is True
    assert saved_group.permissions["canManageSdkKeys"] is True
    assert saved_group.permissions["canManageWebhooks"] is False
