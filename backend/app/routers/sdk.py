from __future__ import annotations

"""SDK router — public config.json endpoint (no auth required)."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.config_json import generate_config_json

router = APIRouter(prefix="/api/v1/sdk", tags=["SDK"])


@router.get("/{sdk_key}/config.json")
async def get_config_json(
    sdk_key: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no authentication required.
    
    SDKs poll this endpoint to fetch the config JSON,
    then evaluate flags client-side using the cached data.
    """
    config_json = await generate_config_json(sdk_key, db)
    if config_json is None:
        raise HTTPException(status_code=404, detail="Invalid or revoked SDK key")

    return Response(
        content=__import__("json").dumps(config_json),
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=60",
            "ETag": str(hash(str(config_json))),
        },
    )
