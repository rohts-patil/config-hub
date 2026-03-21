from __future__ import annotations
from typing import List

"""Product router — CRUD under an organization."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.product import Product
from app.schemas.schemas import ProductCreate, ProductUpdate, ProductOut
from app.services.auth import get_current_user
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/organizations/{org_id}/products", tags=["Products"])


async def _require_org_member(org_id: str, user: User, db: AsyncSession):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")


@router.get("", response_model=List[ProductOut])
async def list_products(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    result = await db.execute(select(Product).where(Product.organization_id == org_id))
    return result.scalars().all()


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    org_id: str,
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    product = Product(
        organization_id=org_id, name=body.name, description=body.description
    )
    db.add(product)
    await db.flush()
    await record_audit(
        db,
        org_id,
        current_user.id,
        "created",
        "product",
        entity_id=product.id,
        new_value={"name": product.name, "description": product.description},
    )
    return product


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    org_id: str,
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    result = await db.execute(
        select(Product).where(
            Product.id == product_id, Product.organization_id == org_id
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    org_id: str,
    product_id: str,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    result = await db.execute(
        select(Product).where(
            Product.id == product_id, Product.organization_id == org_id
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    old_value = {"name": product.name, "description": product.description}
    if body.name is not None:
        product.name = body.name
    if body.description is not None:
        product.description = body.description
    await db.flush()
    await record_audit(
        db,
        org_id,
        current_user.id,
        "updated",
        "product",
        entity_id=product.id,
        old_value=old_value,
        new_value={"name": product.name, "description": product.description},
    )
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    org_id: str,
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    result = await db.execute(
        select(Product).where(
            Product.id == product_id, Product.organization_id == org_id
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await record_audit(
        db,
        org_id,
        current_user.id,
        "deleted",
        "product",
        entity_id=product.id,
        old_value={"name": product.name, "description": product.description},
    )
    await db.delete(product)
