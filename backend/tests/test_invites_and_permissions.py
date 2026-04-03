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
from app.models.organization import (  # noqa: E402
    Organization,
    OrganizationInvite,
    OrganizationMember,
    OrgRole,
)
from app.models.permission import PermissionGroup, ProductPermissionAssignment  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.auth import register  # noqa: E402
from app.routers.audit_log import list_audit_logs  # noqa: E402
from app.routers.organizations import create_invite, delete_member  # noqa: E402
from app.routers.permissions import (  # noqa: E402
    PermissionGroupCreate,
    create_permission_group,
    list_product_member_access,
    update_product_member_access,
)
from app.schemas.schemas import OrgInviteCreate, ProductMemberPermissionUpdate, UserRegister  # noqa: E402
from app.services.audit import record_audit  # noqa: E402
from app.services.authz import require_product_permission  # noqa: E402
from app.services.mailer import EmailConfigurationError  # noqa: E402


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


@pytest.mark.asyncio
async def test_create_invite_marks_email_as_sent(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
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

    async def fake_send_org_invite_email(invite, organization, inviter):
        invite.email_sent_at = invite.created_at
        invite.last_email_error = None

    monkeypatch.setattr(
        "app.routers.organizations.send_org_invite_email",
        fake_send_org_invite_email,
    )

    invite = await create_invite(
        org.id,
        OrgInviteCreate(email="teammate@example.com", role="member"),
        db=db_session,
        current_user=admin,
    )

    assert invite.email == "teammate@example.com"
    assert invite.email_sent_at is not None
    assert invite.last_email_error is None


@pytest.mark.asyncio
async def test_create_invite_persists_delivery_error_without_failing(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
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

    async def fake_send_org_invite_email(invite, organization, inviter):
        raise EmailConfigurationError("SMTP is not configured for invites.")

    monkeypatch.setattr(
        "app.routers.organizations.send_org_invite_email",
        fake_send_org_invite_email,
    )

    invite = await create_invite(
        org.id,
        OrgInviteCreate(email="teammate@example.com", role="member"),
        db=db_session,
        current_user=admin,
    )

    assert invite.email_sent_at is None
    assert invite.last_email_error == "SMTP is not configured for invites."


@pytest.mark.asyncio
async def test_create_invite_respects_disabled_email_config(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
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

    monkeypatch.setattr("app.services.invites.settings.INVITE_EMAILS_ENABLED", False)

    invite = await create_invite(
        org.id,
        OrgInviteCreate(email="teammate@example.com", role="member"),
        db=db_session,
        current_user=admin,
    )

    assert invite.email_sent_at is None
    assert invite.last_email_error is None


@pytest.mark.asyncio
async def test_product_permissions_require_assignment_when_groups_exist(
    db_session: AsyncSession,
):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    member = User(
        email="member@example.com",
        name="Member User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, member, org])
    await db_session.flush()

    admin_membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    member_membership = OrganizationMember(
        organization_id=org.id,
        user_id=member.id,
        role=OrgRole.MEMBER,
    )
    product = Product(
        organization_id=org.id,
        name="Checkout",
        description="Main product",
    )
    db_session.add_all([admin_membership, member_membership, product])
    await db_session.flush()

    group = await create_permission_group(
        product.id,
        PermissionGroupCreate(
            name="Release Managers",
            permissions={"canManageFlags": True},
        ),
        db=db_session,
        current_user=admin,
    )

    with pytest.raises(HTTPException) as exc:
        await require_product_permission(
            db_session,
            product.id,
            member,
            "canManageFlags",
        )

    assert exc.value.status_code == 403

    assignment = ProductPermissionAssignment(
        product_id=product.id,
        organization_member_id=member_membership.id,
        permission_group_id=group.id,
    )
    db_session.add(assignment)
    await db_session.flush()

    allowed_product = await require_product_permission(
        db_session,
        product.id,
        member,
        "canManageFlags",
    )

    assert allowed_product.id == product.id


@pytest.mark.asyncio
async def test_org_admin_can_assign_permission_groups_to_members(
    db_session: AsyncSession,
):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    member = User(
        email="member@example.com",
        name="Member User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, member, org])
    await db_session.flush()

    admin_membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    member_membership = OrganizationMember(
        organization_id=org.id,
        user_id=member.id,
        role=OrgRole.MEMBER,
    )
    product = Product(
        organization_id=org.id,
        name="Checkout",
        description="Main product",
    )
    db_session.add_all([admin_membership, member_membership, product])
    await db_session.flush()

    group = await create_permission_group(
        product.id,
        PermissionGroupCreate(
            name="Release Managers",
            permissions={"canManageFlags": True, "canManageSdkKeys": True},
        ),
        db=db_session,
        current_user=admin,
    )

    updated_access = await update_product_member_access(
        product.id,
        member_membership.id,
        ProductMemberPermissionUpdate(permission_group_id=group.id),
        db=db_session,
        current_user=admin,
    )

    access_rows = await list_product_member_access(
        product.id,
        db=db_session,
        current_user=member,
    )

    assert updated_access.permission_group_id == group.id
    assert updated_access.permission_group_name == "Release Managers"
    assert any(
        row.member_id == member_membership.id
        and row.permission_group_name == "Release Managers"
        for row in access_rows
    )


@pytest.mark.asyncio
async def test_audit_log_requires_explicit_product_audit_access_when_grouped(
    db_session: AsyncSession,
):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    member = User(
        email="member@example.com",
        name="Member User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, member, org])
    await db_session.flush()

    admin_membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    member_membership = OrganizationMember(
        organization_id=org.id,
        user_id=member.id,
        role=OrgRole.MEMBER,
    )
    product = Product(
        organization_id=org.id,
        name="Checkout",
        description="Main product",
    )
    db_session.add_all([admin_membership, member_membership, product])
    await db_session.flush()

    await record_audit(
        db_session,
        org.id,
        admin.id,
        "updated",
        "product",
        product_id=product.id,
        entity_id=product.id,
        new_value={"name": product.name},
    )

    await create_permission_group(
        product.id,
        PermissionGroupCreate(
            name="Release Managers",
            permissions={"canManageFlags": True},
        ),
        db=db_session,
        current_user=admin,
    )

    with pytest.raises(HTTPException) as exc:
        await list_audit_logs(
            org.id,
            entity_type=None,
            action=None,
            limit=50,
            offset=0,
            db=db_session,
            current_user=member,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_returns_scoped_entries_for_assigned_member(
    db_session: AsyncSession,
):
    admin = User(
        email="admin@example.com",
        name="Admin User",
        password_hash="hashed",
    )
    member = User(
        email="member@example.com",
        name="Member User",
        password_hash="hashed",
    )
    org = Organization(name="Acme")
    db_session.add_all([admin, member, org])
    await db_session.flush()

    admin_membership = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role=OrgRole.ADMIN,
    )
    member_membership = OrganizationMember(
        organization_id=org.id,
        user_id=member.id,
        role=OrgRole.MEMBER,
    )
    allowed_product = Product(
        organization_id=org.id,
        name="Checkout",
        description="Main product",
    )
    blocked_product = Product(
        organization_id=org.id,
        name="Billing",
        description="Billing product",
    )
    db_session.add_all(
        [admin_membership, member_membership, allowed_product, blocked_product]
    )
    await db_session.flush()

    audit_group = await create_permission_group(
        allowed_product.id,
        PermissionGroupCreate(
            name="Auditors",
            permissions={"canViewAuditLog": True},
        ),
        db=db_session,
        current_user=admin,
    )
    await create_permission_group(
        blocked_product.id,
        PermissionGroupCreate(
            name="Restricted",
            permissions={"canManageFlags": True},
        ),
        db=db_session,
        current_user=admin,
    )

    assignment = ProductPermissionAssignment(
        product_id=allowed_product.id,
        organization_member_id=member_membership.id,
        permission_group_id=audit_group.id,
    )
    db_session.add(assignment)
    await db_session.flush()

    await record_audit(
        db_session,
        org.id,
        admin.id,
        "updated",
        "product",
        product_id=allowed_product.id,
        entity_id=allowed_product.id,
        new_value={"name": allowed_product.name},
    )
    await record_audit(
        db_session,
        org.id,
        admin.id,
        "updated",
        "product",
        product_id=blocked_product.id,
        entity_id=blocked_product.id,
        new_value={"name": blocked_product.name},
    )

    logs = await list_audit_logs(
        org.id,
        entity_type=None,
        action=None,
        limit=50,
        offset=0,
        db=db_session,
        current_user=member,
    )

    assert len(logs) >= 1
    assert all(entry.context is None or entry.context.product_name != "Billing" for entry in logs)
    assert any(entry.context and entry.context.product_name == "Checkout" for entry in logs)
