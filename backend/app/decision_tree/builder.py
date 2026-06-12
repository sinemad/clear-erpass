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
    ServiceTree,
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


# ----------------------------------------------------------------------
# Service tree (structural / blueprint view)
# ----------------------------------------------------------------------

def build_service_tree(service: dict[str, Any]) -> ServiceTree:
    """Build a structural ServiceTree from a raw ClearPass service dict.

    Produces one node per configured policy stage (service match,
    authentication, authorization, role mapping, posture, enforcement,
    result), connected top-to-bottom. All nodes use NOT_EVALUATED status
    because this is a blueprint, not a traversal record.
    """
    nodes: list[DecisionNode] = []
    edges: list[DecisionEdge] = []
    y = 0
    y_step = 150
    x_center = 0
    prev_id: str | None = None
    order = 0

    def _add(node_id: str, label: str, stage: EvaluationStage,
             summary: str | None = None, details: dict[str, str] | None = None) -> None:
        nonlocal y, prev_id, order
        nodes.append(DecisionNode(
            id=node_id,
            position=Position(x=x_center, y=y),
            data=DecisionNodeData(
                label=label,
                stage=stage,
                status=EvaluationStatus.NOT_EVALUATED,
                summary=summary,
                details=details or {},
            ),
        ))
        if prev_id is not None:
            order += 1
            edges.append(DecisionEdge(
                id=f"e{order}", source=prev_id, target=node_id,
                order=order, animated=False,
            ))
        prev_id = node_id
        y += y_step

    name = service.get("name", "Unknown Service")
    svc_type = str(service.get("type") or "")

    _add("service", f"Service: {name}", EvaluationStage.SERVICE_MATCH,
         summary=svc_type or None,
         details={"type": svc_type} if svc_type else {})

    # Authentication
    auth_methods = service.get("authentication_methods") or []
    auth_sources = service.get("authentication_sources") or []
    if auth_methods or auth_sources:
        details: dict[str, str] = {}
        if auth_methods:
            details["methods"] = ", ".join(auth_methods) if isinstance(auth_methods, list) else str(auth_methods)
        if auth_sources:
            details["sources"] = ", ".join(auth_sources) if isinstance(auth_sources, list) else str(auth_sources)
        _add("authentication", "Authentication", EvaluationStage.AUTHENTICATION,
             summary=details.get("methods") or details.get("sources"), details=details)

    # Authorization
    authz_sources = service.get("authorization_sources") or []
    if authz_sources:
        src_str = ", ".join(authz_sources) if isinstance(authz_sources, list) else str(authz_sources)
        _add("authorization", "Authorization", EvaluationStage.AUTHORIZATION,
             summary=src_str, details={"sources": src_str})

    # Role mapping
    role_policy = service.get("role_mapping_policy") or service.get("role_policy")
    if role_policy:
        _add("role_mapping", "Role Mapping", EvaluationStage.ROLE_MAPPING,
             summary=str(role_policy), details={"policy": str(role_policy)})

    # Posture
    posture_policy = service.get("posture_policy")
    if posture_policy:
        _add("posture", "Posture", EvaluationStage.POSTURE,
             summary=str(posture_policy), details={"policy": str(posture_policy)})

    # Enforcement
    enforcement_policy = service.get("enforcement_policy")
    if enforcement_policy:
        _add("enforcement", "Enforcement", EvaluationStage.ENFORCEMENT,
             summary=str(enforcement_policy), details={"policy": str(enforcement_policy)})

    _add("result", "Result", EvaluationStage.RESULT)

    return ServiceTree(
        service_id=str(service.get("id", "")),
        service_name=name,
        service_type=svc_type or None,
        nodes=nodes,
        edges=edges,
    )
