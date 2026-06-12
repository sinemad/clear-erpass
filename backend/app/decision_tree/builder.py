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

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("app.decision_tree")

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

# Layout constants (pixels — React Flow coordinate space)
_MAIN_X = 0        # x of the main pipeline nodes
_DETAIL_X = 380    # x of the rule/detail sub-nodes
_PROFILE_X = 720   # x of enforcement profile output nodes
_STAGE_H = 90      # approximate rendered height of a main stage node
_RULE_H = 75       # approximate rendered height of a rule/detail node
_STAGE_GAP = 60    # vertical gap between stage groups


def _fmt_conditions(conditions: Any) -> str:
    """Condense a ClearPass conditions list into a short readable string."""
    if not conditions:
        return ""
    if isinstance(conditions, str):
        return conditions[:100]
    items: list[str] = []
    for cond in (conditions if isinstance(conditions, list) else [conditions]):
        if not isinstance(cond, dict):
            items.append(str(cond)[:60])
            continue
        attr = cond.get("attribute") or cond.get("name") or cond.get("type") or ""
        op   = cond.get("operator") or cond.get("oper") or "="
        val  = cond.get("value") or cond.get("operand") or ""
        if attr:
            items.append(f"{attr} {op} {val}".strip())
        if len(items) >= 2:
            break
    remainder = len(conditions) - len(items) if isinstance(conditions, list) else 0
    result = " AND ".join(items)
    return f"{result} (+{remainder} more)" if remainder > 0 else result


def _extract_name(item: Any) -> str:
    """Pull a human-readable name out of a ClearPass object or plain string."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(
            item.get("name") or item.get("role_name") or item.get("profile_name")
            or item.get("label") or next(iter(item.values()), "")
        )
    return str(item)


def _fmt_list(val: Any) -> str:
    if isinstance(val, list):
        return ", ".join(_extract_name(v) for v in val if v)
    if isinstance(val, dict):
        return _extract_name(val)
    return str(val) if val else ""


def _policy_details(obj: dict[str, Any], *skip_keys: str) -> dict[str, str]:
    """Extract human-readable key/value pairs from a policy dict."""
    skip = {"id", "name", "description", "_embedded", "_links", "rules",
            "rule_combine_algo", *skip_keys}
    out: dict[str, str] = {}
    for k, v in obj.items():
        if k in skip or v is None or v == "" or v == []:
            continue
        out[k] = _fmt_list(v) if isinstance(v, list) else str(v)
    return out


def build_service_tree(service: dict[str, Any], policies: dict[str, Any] | None = None) -> ServiceTree:
    """Build a structural ServiceTree from a raw ClearPass service dict.

    Parameters
    ----------
    service:
        Raw service dict from ClearPassClient.get_service().
    policies:
        Pre-fetched policy objects keyed by type. Expected keys:
        ``auth_methods``, ``auth_sources``, ``role_mapping``,
        ``posture_policy``, ``enforcement_policy``.
        Pass None (or omit) to build a minimal tree without sub-nodes.
    """
    p = policies or {}
    nodes: list[DecisionNode] = []
    edges: list[DecisionEdge] = []
    edge_order = 0
    prev_pipeline_id: str | None = None
    current_y = 0

    def _add_main(node_id: str, label: str, stage: EvaluationStage,
                  summary: str | None, details: dict[str, str],
                  n_children: int) -> None:
        nonlocal prev_pipeline_id, edge_order, current_y
        # Centre the main node vertically over its children
        group_h = max(_STAGE_H, n_children * _RULE_H)
        node_y = current_y + (group_h - _STAGE_H) // 2
        nodes.append(DecisionNode(
            id=node_id,
            position=Position(x=_MAIN_X, y=node_y),
            data=DecisionNodeData(
                label=label, stage=stage,
                status=EvaluationStatus.NOT_EVALUATED,
                summary=summary, details=details,
            ),
        ))
        if prev_pipeline_id:
            edge_order += 1
            edges.append(DecisionEdge(
                id=f"e{edge_order}", source=prev_pipeline_id, target=node_id,
                order=edge_order, animated=False,
            ))
        prev_pipeline_id = node_id
        return node_y  # type: ignore[return-value]  # intentional dual return

    def _add_child(child_id: str, parent_id: str, label: str, stage: EvaluationStage,
                   summary: str | None, details: dict[str, str], child_y: int) -> None:
        nonlocal edge_order
        nodes.append(DecisionNode(
            id=child_id, type="policyRuleNode",
            position=Position(x=_DETAIL_X, y=child_y),
            data=DecisionNodeData(
                label=label, stage=stage,
                status=EvaluationStatus.NOT_EVALUATED,
                summary=summary, details=details,
            ),
        ))
        edge_order += 1
        edges.append(DecisionEdge(
            id=f"e{edge_order}", source=parent_id, target=child_id,
            order=edge_order, animated=False,
        ))

    def _advance(n_children: int) -> None:
        nonlocal current_y
        current_y += max(_STAGE_H, n_children * _RULE_H) + _STAGE_GAP

    logger.info("build_service_tree keys=%s", sorted(service.keys()))

    name = service.get("name", "Unknown Service")
    svc_type = str(service.get("type") or "")

    # ---- Service Match ----
    svc_details: dict[str, str] = {}
    if svc_type:
        svc_details["type"] = svc_type
    if service.get("template"):
        svc_details["template"] = str(service["template"])
    if service.get("description"):
        svc_details["description"] = str(service["description"])
    _add_main("service", f"Service: {name}", EvaluationStage.SERVICE_MATCH,
              svc_type or None, svc_details, 0)
    _advance(0)

    # ---- Authentication ----
    auth_method_objs: list[dict] = p.get("auth_methods") or []
    auth_source_objs: list[dict] = p.get("auth_sources") or []
    auth_method_names: list[str] = service.get("authentication_methods") or []
    auth_source_names: list[str] = service.get("authentication_sources") or []

    if auth_method_names or auth_source_names:
        n_auth = len(auth_method_objs) + len(auth_source_objs) or (
            len(auth_method_names) + len(auth_source_names)
        )
        auth_summary = _fmt_list(auth_method_names) or _fmt_list(auth_source_names)
        _add_main("authentication", "Authentication", EvaluationStage.AUTHENTICATION,
                  auth_summary or None, {}, n_auth)
        child_y = current_y
        for i, method_obj in enumerate(auth_method_objs):
            m_name = method_obj.get("name", auth_method_names[i] if i < len(auth_method_names) else f"Method {i+1}")
            m_type = method_obj.get("method_type") or method_obj.get("inner_method") or ""
            _add_child(f"auth_method_{i}", "authentication", m_name,
                       EvaluationStage.AUTHENTICATION,
                       m_type or None, _policy_details(method_obj), child_y)
            child_y += _RULE_H
        # Fallback: if we have names but no objects, still show name nodes
        if not auth_method_objs:
            for i, m_name in enumerate(auth_method_names):
                _add_child(f"auth_method_{i}", "authentication", m_name,
                           EvaluationStage.AUTHENTICATION, None, {}, child_y)
                child_y += _RULE_H
        for i, src_obj in enumerate(auth_source_objs):
            s_name = src_obj.get("name", auth_source_names[i] if i < len(auth_source_names) else f"Source {i+1}")
            s_type = src_obj.get("type") or src_obj.get("source_type") or ""
            _add_child(f"auth_source_{i}", "authentication", s_name,
                       EvaluationStage.AUTHORIZATION,
                       s_type or None, _policy_details(src_obj), child_y)
            child_y += _RULE_H
        if not auth_source_objs:
            for i, s_name in enumerate(auth_source_names):
                _add_child(f"auth_source_{i}", "authentication", s_name,
                           EvaluationStage.AUTHORIZATION, None, {}, child_y)
                child_y += _RULE_H
        _advance(n_auth)

    # ---- Role Mapping ----
    role_policy_name = service.get("role_mapping_policy") or service.get("role_policy") or ""
    role_mapping_obj: dict | None = p.get("role_mapping")
    if role_policy_name:
        rules: list[dict] = []
        if role_mapping_obj:
            rules = role_mapping_obj.get("rules") or []
        rm_details: dict[str, str] = {"policy": role_policy_name}
        if role_mapping_obj:
            rm_details.update(_policy_details(role_mapping_obj, "rules"))
        _add_main("role_mapping", "Role Mapping", EvaluationStage.ROLE_MAPPING,
                  role_policy_name, rm_details, len(rules))
        for i, rule in enumerate(rules):
            logger.debug("role_mapping rule[%d] keys=%s raw=%r", i, list(rule.keys()), rule)
            conditions = rule.get("conditions") or rule.get("condition") or []
            roles_assigned = (
                rule.get("roles")
                or rule.get("role")
                or rule.get("role_name")
                or rule.get("role_names")
                or rule.get("assigned_roles")
                or []
            )
            # Unwrap single-item non-list shapes
            if isinstance(roles_assigned, (str, dict)):
                roles_assigned = [roles_assigned]
            cond_str = _fmt_conditions(conditions)
            roles_str = _fmt_list(roles_assigned)

            # Fallback: capture any non-condition, non-system fields we don't recognise
            # so the drawer always shows the outcome even if the field name is unexpected
            if not roles_str:
                _known = {"id", "conditions", "condition", "roles", "role", "role_name",
                          "role_names", "assigned_roles", "rule_combine_algo"}
                for k, v in rule.items():
                    if k not in _known and v:
                        roles_str = _fmt_list(v)
                        logger.debug("role_mapping rule[%d] using fallback field %r = %r", i, k, roles_str)
                        break

            label = cond_str or f"Rule {i + 1}"
            summary = roles_str or None
            child_details: dict[str, str] = {"Order": str(i + 1)}
            if cond_str:
                child_details["conditions"] = cond_str
            if roles_str:
                child_details["roles"] = roles_str
            _add_child(f"rm_rule_{i}", "role_mapping", label,
                       EvaluationStage.ROLE_MAPPING, summary, child_details,
                       current_y + i * _RULE_H)
        _advance(max(1, len(rules)))

    # ---- Posture ----
    posture_name = service.get("posture_policy") or ""
    posture_obj: dict | None = p.get("posture_policy")
    if posture_name:
        posture_rules: list[dict] = posture_obj.get("rules") or [] if posture_obj else []
        posture_details: dict[str, str] = {"policy": posture_name}
        if posture_obj:
            posture_details.update(_policy_details(posture_obj, "rules"))
        _add_main("posture", "Posture", EvaluationStage.POSTURE,
                  posture_name, posture_details, len(posture_rules))
        for i, rule in enumerate(posture_rules):
            cond_str = _fmt_conditions(rule.get("conditions") or rule.get("condition") or [])
            extra = {k: str(v) for k, v in rule.items() if v and k not in ("conditions",)}
            posture_child_details: dict[str, str] = {"Order": str(i + 1), **extra}
            if cond_str:
                posture_child_details["conditions"] = cond_str
            _add_child(f"posture_rule_{i}", "posture", cond_str or f"Rule {i + 1}",
                       EvaluationStage.POSTURE, None,
                       posture_child_details,
                       current_y + i * _RULE_H)
        _advance(max(1, len(posture_rules)))

    # ---- Enforcement ----
    enforcement_name = (
        service.get("enforcement_policy")
        or service.get("enforcement_policy_name")
        or service.get("enforcement_policies")   # some versions use this
        or service.get("enforcement")
        or ""
    )
    # enforcement_policies may be a list — take first entry
    if isinstance(enforcement_name, list):
        enforcement_name = enforcement_name[0] if enforcement_name else ""
    if isinstance(enforcement_name, dict):
        enforcement_name = enforcement_name.get("name") or ""
    enforcement_name = str(enforcement_name).strip()
    logger.info("enforcement_name resolved to %r", enforcement_name)
    enforcement_obj: dict | None = p.get("enforcement_policy")
    enf_profile_objs: list[dict] = p.get("enforcement_profiles") or []

    if enforcement_name:
        enforcement_rules: list[dict] = enforcement_obj.get("rules") or [] if enforcement_obj else []
        enf_details: dict[str, str] = {"policy": enforcement_name}
        if enforcement_obj:
            enf_details.update(_policy_details(enforcement_obj, "rules"))
        _add_main("enforcement", "Enforcement", EvaluationStage.ENFORCEMENT,
                  enforcement_name, enf_details, len(enforcement_rules))

        profile_obj_by_name: dict[str, dict] = {
            obj.get("name", ""): obj for obj in enf_profile_objs if obj.get("name")
        }
        profile_y = current_y  # independent y counter for the third column

        for i, rule in enumerate(enforcement_rules):
            conditions = rule.get("conditions") or rule.get("condition") or []
            rule_profiles = (
                rule.get("enforcement_profiles")
                or rule.get("profiles")
                or rule.get("profile")
                or []
            )
            if isinstance(rule_profiles, (str, dict)):
                rule_profiles = [rule_profiles]

            cond_str = _fmt_conditions(conditions)
            prof_str = _fmt_list(rule_profiles)
            rule_y = current_y + i * _RULE_H
            label = cond_str or f"Rule {i + 1}"
            enf_child_details: dict[str, str] = {"Order": str(i + 1)}
            if cond_str:
                enf_child_details["conditions"] = cond_str
            if prof_str:
                enf_child_details["profiles"] = prof_str
            _add_child(f"enf_rule_{i}", "enforcement", label,
                       EvaluationStage.ENFORCEMENT, prof_str or None, enf_child_details,
                       rule_y)

            # Add enforcement profile nodes in the third column
            for j, rp in enumerate(rule_profiles):
                prof_name = _extract_name(rp)
                if not prof_name:
                    continue
                prof_node_id = f"enf_profile_{prof_name.replace(' ', '_')}"
                # Only add each unique profile once
                if not any(n.id == prof_node_id for n in nodes):
                    prof_obj = profile_obj_by_name.get(prof_name, {})
                    prof_type = prof_obj.get("type") or prof_obj.get("profile_type") or ""
                    prof_details = _policy_details(prof_obj) if prof_obj else {}
                    nodes.append(DecisionNode(
                        id=prof_node_id,
                        type="enfProfileNode",
                        position=Position(x=_PROFILE_X, y=profile_y),
                        data=DecisionNodeData(
                            label=prof_name,
                            stage=EvaluationStage.ENFORCEMENT,
                            status=EvaluationStatus.NOT_EVALUATED,
                            summary=prof_type or None,
                            details=prof_details,
                        ),
                    ))
                    profile_y += _RULE_H
                edge_order += 1
                edges.append(DecisionEdge(
                    id=f"e{edge_order}",
                    source=f"enf_rule_{i}",
                    target=prof_node_id,
                    order=edge_order,
                    animated=False,
                ))

        n_rows = max(len(enforcement_rules), len(enf_profile_objs), 1)
        _advance(n_rows)

    return ServiceTree(
        service_id=str(service.get("id", "")),
        service_name=name,
        service_type=svc_type or None,
        nodes=nodes,
        edges=edges,
    )
