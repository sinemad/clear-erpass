"""Access Tracker API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.clearpass.client import ClearPassClient, get_clearpass_client
from app.models.access_tracker import AccessTrackerDetail, AccessTrackerSummary

logger = logging.getLogger("app.api.access_tracker")
router = APIRouter(prefix="/api/access-tracker", tags=["access-tracker"])


def _build_filter(
    start_time: datetime | None,
    end_time: datetime | None,
    service_name: str | None,
    username: str | None,
    result: str | None,
) -> dict:
    """Build the ClearPass API JSON filter expression.

    Only includes fields the caller explicitly provides. Time range filtering
    is omitted by default because ClearPass's timestamp range syntax varies
    across versions and can cause the endpoint to return 404 instead of results.
    """
    f: dict = {}
    if service_name:
        f["service_name"] = service_name
    if username:
        f["username"] = username
    if result:
        f["auth_status"] = result.upper()
    if start_time:
        f["timestamp"] = {"$ge": start_time.isoformat()}
        if end_time:
            f["timestamp"]["$le"] = end_time.isoformat()
    return f


@router.get("", response_model=list[AccessTrackerSummary])
async def list_access_tracker_records(
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
    start_time: Annotated[
        datetime | None,
        Query(description="Only return records on/after this timestamp (ISO 8601)."),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Only return records on/before this timestamp (ISO 8601)."),
    ] = None,
    service_name: Annotated[
        str | None, Query(description="Filter by exact service name.")
    ] = None,
    username: Annotated[str | None, Query(description="Filter by username.")] = None,
    result: Annotated[
        str | None, Query(description="Filter by result: ACCEPT, REJECT, DROP.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AccessTrackerSummary]:
    """List Access Tracker records with optional filtering."""
    logger.debug(
        "list_access_tracker_records: service=%r user=%r result=%r limit=%d offset=%d",
        service_name, username, result, limit, offset,
    )
    filter_query = _build_filter(start_time, end_time, service_name, username, result)
    try:
        raw_records = await run_in_threadpool(
            client.list_access_tracker_records,
            filter_query=filter_query,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("list_access_tracker_records failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    logger.debug("list_access_tracker_records returning %d record(s)", len(raw_records))
    return [AccessTrackerSummary.model_validate(r) for r in raw_records]


@router.get("/{record_id}", response_model=AccessTrackerDetail)
async def get_access_tracker_record(
    record_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> AccessTrackerDetail:
    """Return the full detail of a single Access Tracker record."""
    logger.debug("get_access_tracker_record: id=%s", record_id)
    try:
        raw = await run_in_threadpool(client.get_access_tracker_record, record_id)
    except Exception as exc:
        logger.error("get_access_tracker_record id=%s failed: %s", record_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Access Tracker record '{record_id}' not found")

    return AccessTrackerDetail.model_validate(raw)


@router.get("/{record_id}/decision-tree")
async def get_access_tracker_decision_tree(
    record_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
):
    """Return the decision tree for a single Access Tracker record."""
    from app.decision_tree.builder import build_decision_tree
    from app.models.decision_tree import DecisionTree

    logger.debug("get_access_tracker_decision_tree: id=%s", record_id)
    try:
        raw = await run_in_threadpool(client.get_access_tracker_record, record_id)
    except Exception as exc:
        logger.error("get_access_tracker_decision_tree id=%s failed: %s", record_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Access Tracker record '{record_id}' not found")

    return build_decision_tree(raw)
