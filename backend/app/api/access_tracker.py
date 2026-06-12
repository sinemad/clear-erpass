"""
Access Tracker API routes.

Exposes read-only endpoints for browsing Access Tracker records and
retrieving the decision tree view for a specific record.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.clearpass.client import ClearPassClient, get_clearpass_client
from app.decision_tree.builder import build_decision_tree
from app.models.access_tracker import AccessTrackerSummary  # TODO: define this model
from app.models.decision_tree import DecisionTree

logger = logging.getLogger("app.api.access_tracker")
router = APIRouter(prefix="/api/access-tracker", tags=["access-tracker"])


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
    username: Annotated[
        str | None, Query(description="Filter by username/identity.")
    ] = None,
    result: Annotated[
        str | None,
        Query(description="Filter by final result, e.g. ACCEPT, REJECT, DROP."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AccessTrackerSummary]:
    """List Access Tracker records, with basic filtering and pagination.

    This endpoint backs the Access Tracker table view. It should default to
    a recent time window (e.g. last 24h) if `start_time`/`end_time` are not
    provided -- enforce that default in the ClearPass client / filter
    construction below.

    TODO:
    - Build the ClearPass filter_query dict from the query params above.
    - Apply a default time window when start_time/end_time are both None.
    - Map each raw record to `AccessTrackerSummary` (id, timestamp, service
      name, username, endpoint MAC, result, etc.) -- keep this mapping in
      `app/clearpass/mapping.py` or similar rather than inline here.
    - Consider caching results in SQLite (see CLAUDE.md) and serving from
      cache with a background refresh, rather than calling ClearPass
      synchronously on every request.
    """
    logger.debug(
        "list_access_tracker_records requested (start=%s, end=%s, service=%s, user=%s, result=%s, limit=%d, offset=%d)",
        start_time, end_time, service_name, username, result, limit, offset,
    )
    filter_query: dict = {}  # TODO: build from start_time/end_time/service_name/username/result

    try:
        raw_records = await run_in_threadpool(
            client.list_access_tracker_records,
            filter_query=filter_query,
            limit=limit,
            offset=offset,
        )
    except NotImplementedError:
        logger.warning("list_access_tracker_records: ClearPass client not yet implemented")
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        logger.error("list_access_tracker_records failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    logger.debug("list_access_tracker_records returning %d record(s)", len(raw_records))
    # TODO: replace with real mapping once AccessTrackerSummary fields and
    # raw record field names are finalized.
    return [AccessTrackerSummary.model_validate(r) for r in raw_records]


@router.get("/{record_id}/decision-tree", response_model=DecisionTree)
async def get_access_tracker_decision_tree(
    record_id: str,
    client: Annotated[ClearPassClient, Depends(get_clearpass_client)],
) -> DecisionTree:
    """Return the decision tree for a single Access Tracker record.

    This is the primary endpoint backing the animated decision tree view.

    Raises
    ------
    404 if the record does not exist / ClearPass returns no data.
    502 if the ClearPass API call fails unexpectedly.
    """
    logger.debug("get_access_tracker_decision_tree requested: id=%s", record_id)
    try:
        raw_record = await run_in_threadpool(client.get_access_tracker_record, record_id)
    except NotImplementedError:
        logger.warning("get_access_tracker_decision_tree: ClearPass client not yet implemented")
        raise HTTPException(status_code=501, detail="ClearPass client not yet implemented")
    except Exception as exc:
        logger.error("get_access_tracker_decision_tree id=%s failed: %s", record_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"ClearPass API error: {exc}") from exc

    if not raw_record:
        logger.info("Access Tracker record id=%s not found", record_id)
        raise HTTPException(status_code=404, detail=f"Access Tracker record '{record_id}' not found")

    logger.info("Building decision tree for record id=%s", record_id)
    return build_decision_tree(raw_record)
