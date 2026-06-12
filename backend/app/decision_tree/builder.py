"""
Decision tree builder.

Converts a raw ClearPass Access Tracker / Insight record (as returned by
`ClearPassClient.get_access_tracker_record`) into the `DecisionTree` Pydantic
model defined in `backend/app/models/decision_tree.py`.

This is the core "domain logic" of the visualizer: it maps ClearPass's
representation of a policy evaluation (whatever shape that turns out to be
for your ClearPass version) onto a generic node/edge/path structure that the
frontend can render with React Flow and animate.

Suggested approach
-------------------
1. Start by fetching one real Access Tracker record's full JSON via
   `ClearPassClient.get_access_tracker_record()` and inspect its shape
   (service name, auth method/source, role mapping rule matched, posture
   results, enforcement profiles applied, final result).
2. Identify, for a "happy path" record, the ordered list of evaluation steps
   you want to show as nodes (typically: service match -> authentication ->
   role mapping -> posture (if used) -> enforcement -> result).
3. Implement `_build_nodes_and_edges` below to extract those steps from the
   raw record and produce `DecisionNode`/`DecisionEdge` lists plus the
   traversal `path`.
4. Handle "not evaluated" branches (e.g. posture skipped, role mapping rules
   that didn't match) as nodes with `status="not_evaluated"` so the frontend
   can render the full possible tree dimmed, with only `path` highlighted.

This module deliberately has NO dependency on `pyclearpass` -- it only
operates on the raw dict returned by `ClearPassClient`, so it can be
unit-tested with fixture JSON files without hitting a real ClearPass server.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.decision_tree import (
    DecisionEdge,
    DecisionNode,
    DecisionNodeData,
    DecisionTree,
    EvaluationStage,
    EvaluationStatus,
    Position,
)


def build_decision_tree(record: dict[str, Any]) -> DecisionTree:
    """Build a `DecisionTree` from a raw Access Tracker record.

    Parameters
    ----------
    record:
        Raw dict as returned by `ClearPassClient.get_access_tracker_record`.

    Returns
    -------
    DecisionTree
        Ready to be returned directly from the
        `GET /api/access-tracker/{record_id}/decision-tree` endpoint.
    """
    nodes, edges, path = _build_nodes_and_edges(record)

    return DecisionTree(
        record_id=_get_record_id(record),
        service_name=_get_service_name(record),
        request_timestamp=_get_request_timestamp(record),
        final_result=_get_final_result(record),
        nodes=nodes,
        edges=edges,
        path=path,
    )


# ----------------------------------------------------------------------
# Field extraction helpers
#
# TODO: each of these needs to be adjusted to match the actual field names
# present in your ClearPass version's Access Tracker / Insight record JSON.
# Suggested field names below are reasonable guesses based on common
# ClearPass terminology, not confirmed against a live response.
# ----------------------------------------------------------------------

def _get_record_id(record: dict[str, Any]) -> str:
    # TODO: confirm field name, e.g. record.get("id") or record.get("session_id")
    return str(record.get("id", "unknown"))


def _get_service_name(record: dict[str, Any]) -> str:
    # TODO: confirm field name, e.g. record.get("service_name")
    return record.get("service_name", "Unknown Service")


def _get_request_timestamp(record: dict[str, Any]) -> datetime:
    # TODO: confirm field name/format, e.g. record.get("date_time")
    raw = record.get("date_time")
    if raw:
        return datetime.fromisoformat(raw)
    return datetime.utcnow()


def _get_final_result(record: dict[str, Any]) -> EvaluationStatus:
    # TODO: confirm field name/values, e.g. record.get("status") in
    # {"ACCEPT", "REJECT", "DROP"}
    status = (record.get("status") or "").upper()
    if status == "ACCEPT":
        return EvaluationStatus.PASSED
    if status in {"REJECT", "DROP"}:
        return EvaluationStatus.FAILED
    return EvaluationStatus.NOT_EVALUATED


# ----------------------------------------------------------------------
# Core tree construction
# ----------------------------------------------------------------------

def _build_nodes_and_edges(
    record: dict[str, Any],
) -> tuple[list[DecisionNode], list[DecisionEdge], list[str]]:
    """Build the node list, edge list, and traversal path for a record.

    The implementation below is a SKELETON producing a fixed-shape tree
    (service match -> authentication -> role mapping -> enforcement ->
    result) with placeholder data, so the API/frontend can be wired up and
    tested end-to-end before the real ClearPass field mappings are in place.

    Replace the placeholder `DecisionNodeData(...)` calls with values pulled
    from `record` once the real field names are confirmed (see helper
    functions above and the module docstring).
    """

    y_step = 150  # vertical spacing for the default layered layout

    nodes: list[DecisionNode] = [
        DecisionNode(
            id="service_match",
            position=Position(x=0, y=0 * y_step),
            data=DecisionNodeData(
                label=f"Service: {_get_service_name(record)}",
                stage=EvaluationStage.SERVICE_MATCH,
                status=EvaluationStatus.MATCHED,
                summary="Request matched service categorization rules",
                details={},  # TODO: populate from record (e.g. service category, conditions)
            ),
        ),
        DecisionNode(
            id="authentication",
            position=Position(x=0, y=1 * y_step),
            data=DecisionNodeData(
                label="Authentication",
                stage=EvaluationStage.AUTHENTICATION,
                status=EvaluationStatus.PASSED,  # TODO: derive from record
                summary=None,  # TODO: e.g. "EAP-PEAP against Active Directory"
                details={},  # TODO: e.g. {"method": ..., "source": ...}
            ),
        ),
        DecisionNode(
            id="role_mapping",
            position=Position(x=0, y=2 * y_step),
            data=DecisionNodeData(
                label="Role Mapping",
                stage=EvaluationStage.ROLE_MAPPING,
                status=EvaluationStatus.MATCHED,  # TODO: derive from record
                summary=None,  # TODO: e.g. "Matched rule 3: AD-Group contains Contractors"
                details={},  # TODO: e.g. {"rule": ..., "attribute": ..., "value": ...}
            ),
        ),
        DecisionNode(
            id="enforcement",
            position=Position(x=0, y=3 * y_step),
            data=DecisionNodeData(
                label="Enforcement",
                stage=EvaluationStage.ENFORCEMENT,
                status=EvaluationStatus.MATCHED,  # TODO: derive from record
                summary=None,  # TODO: e.g. "Applied 'Contractor VLAN 20' profile"
                details={},  # TODO: e.g. {"profile": ..., "vlan": ...}
            ),
        ),
        DecisionNode(
            id="result",
            position=Position(x=0, y=4 * y_step),
            data=DecisionNodeData(
                label=f"Result: {_get_final_result(record).value.upper()}",
                stage=EvaluationStage.RESULT,
                status=_get_final_result(record),
                summary=None,
                details={},  # TODO: e.g. {"reply_message": ...}
            ),
        ),
    ]

    edges: list[DecisionEdge] = [
        DecisionEdge(id="e1", source="service_match", target="authentication", order=1, animated=True),
        DecisionEdge(id="e2", source="authentication", target="role_mapping", order=2, animated=True),
        DecisionEdge(id="e3", source="role_mapping", target="enforcement", order=3, animated=True),
        DecisionEdge(id="e4", source="enforcement", target="result", order=4, animated=True),
    ]

    path = ["service_match", "authentication", "role_mapping", "enforcement", "result"]

    return nodes, edges, path
