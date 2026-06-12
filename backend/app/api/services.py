"""Services API routes."""

from __future__ import annotations

import logging
from typing import Annotated

import asyncio

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

    # Fetch all referenced policies concurrently — failures are swallowed
    # inside the client so missing policies never block tree rendering.
    auth_method_names: list[str] = service.get("authentication_methods") or []
    auth_source_names: list[str] = service.get("authentication_sources") or []
    role_mapping_name: str = service.get("role_mapping_policy") or ""
    posture_name: str = service.get("posture_policy") or ""
    enforcement_name: str = service.get("enforcement_policy") or ""

    async def fetch_list(names: list[str], fn) -> list[dict]:
        if not names:
            return []
        results = await asyncio.gather(*[run_in_threadpool(fn, n) for n in names])
        return [r for r in results if r]

    async def fetch_one(name: str, fn):
        return await run_in_threadpool(fn, name) if name else None

    auth_methods_data, auth_sources_data, role_mapping_data, posture_data, enforcement_data = (
        await asyncio.gather(
            fetch_list(auth_method_names, client.get_auth_method),
            fetch_list(auth_source_names, client.get_auth_source),
            fetch_one(role_mapping_name, client.get_role_mapping),
            fetch_one(posture_name, client.get_posture_policy),
            fetch_one(enforcement_name, client.get_enforcement_policy),
        )
    )

    policies = {
        "auth_methods": auth_methods_data,
        "auth_sources": auth_sources_data,
        "role_mapping": role_mapping_data,
        "posture_policy": posture_data,
        "enforcement_policy": enforcement_data,
    }

    tree = build_service_tree(service, policies)
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
