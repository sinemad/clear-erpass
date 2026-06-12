"""Services API routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.clearpass.client import ClearPassClient, get_clearpass_client
from app.decision_tree.builder import build_service_tree
from app.models.decision_tree import ServiceTree

logger = logging.getLogger("app.api.services")
router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
async def list_services(
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> list[dict]:
    """Return all configured Policy Manager services."""
    logger.debug("list_services requested")
    try:
        result = await run_in_threadpool(client.list_services)
        logger.debug("list_services returning %d item(s)", len(result))
        return result
    except NotImplementedError:
        logger.warning("list_services: ClearPass client not yet implemented")
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        logger.error("list_services failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc


@router.get("/{service_id}/decision-tree", response_model=ServiceTree)
async def get_service_decision_tree(
    service_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> ServiceTree:
    """Return the structural decision tree for a service.

    This is a blueprint view derived from the service's policy configuration
    (auth methods, role mapping policy, enforcement policy, etc.), not a
    record of a specific evaluation traversal.
    """
    logger.debug("get_service_decision_tree requested: id=%s", service_id)
    try:
        service = await run_in_threadpool(client.get_service, service_id)
    except Exception as exc:
        logger.error("get_service_decision_tree id=%s failed fetching service: %s", service_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

    tree = build_service_tree(service)
    logger.info("Built service tree for id=%s name=%r (%d nodes)", service_id, tree.service_name, len(tree.nodes))
    return tree


@router.get("/{service_id}")
async def get_service(
    service_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> dict:
    """Return a single service definition by ID."""
    logger.debug("get_service requested: id=%s", service_id)
    try:
        service = await run_in_threadpool(client.get_service, service_id)
    except NotImplementedError:
        logger.warning("get_service: ClearPass client not yet implemented")
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        logger.error("get_service id=%s failed: %s", service_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if not service:
        logger.info("get_service: id=%s not found", service_id)
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return service
