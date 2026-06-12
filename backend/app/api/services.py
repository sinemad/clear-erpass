"""Services API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.clearpass.client import ClearPassClient, get_clearpass_client

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
async def list_services(
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> list[dict]:
    """Return all configured Policy Manager services."""
    try:
        return await run_in_threadpool(client.list_services)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc


@router.get("/{service_id}")
async def get_service(
    service_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> dict:
    """Return a single service definition by ID."""
    try:
        service = await run_in_threadpool(client.get_service, service_id)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return service
