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
_MAIN_X = 0        # x of the main pipeline and inline rule nodes
_SIDE_X = 340      # x of supplementary side nodes (auth methods, enforcement profiles)
_STAGE_H = 110     # vertical advance per main stage node
_RULE_H = 90       # vertical advance per inline rule node
_SECTION_GAP = 30  # extra gap between sections


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
    """Build a clean pipeline ServiceTree with rule detail in each node's policy_rules.

    The graph contains only the high-level evaluation stages (Service, Auth,
    Role Mapping, Posture, Enforcement, Access Decision). All rule detail lives
    in node.data.policy_rules and is rendered as a table in the drawer when the
    user clicks a stage node.
    """
    p = policies or {}
    nodes: list[DecisionNode] = []
    edges: list[DecisionEdge] = []
    edge_order = 0
    prev_id: str | None = None
    current_y = 0
    _Y_STEP = 140

    def _stage(node_id: str, label: str, stage: EvaluationStage,
               summary: str | None, details: dict[str, str],
               policy_rules: list[dict[str, str]] | None = None,
               edge_label: str | None = None) -> None:
        nonlocal prev_id, edge_order, current_y
        nodes.append(DecisionNode(
            id=node_id,
            position=Position(x=0, y=current_y),
            data=DecisionNodeData(
                label=label, stage=stage,
                status=EvaluationStatus.NOT_EVALUATED,
                summary=summary, details=details,
                policy_rules=policy_rules or [],
            ),
        ))
        if prev_id:
            edge_order += 1
            edges.append(DecisionEdge(
                id=f"e{edge_order}", source=prev_id, target=node_id,
                order=edge_order, animated=False, label=edge_label,
            ))
        prev_id = node_id
        current_y += _Y_STEP

    def _extract_rm_rule(rule: dict[str, Any], idx: int) -> dict[str, str]:
        conditions = rule.get("conditions") or rule.get("condition") or []
        roles_raw = (
            rule.get("roles") or rule.get("role") or rule.get("role_name")
            or rule.get("role_names") or rule.get("assigned_roles") or []
        )
        if isinstance(roles_raw, (str, dict)):
            roles_raw = [roles_raw]
        cond_str = _fmt_conditions(conditions)
        roles_str = _fmt_list(roles_raw)
        if not roles_str:
            _known = {"id", "conditions", "condition", "roles", "role", "role_name",
                      "role_names", "assigned_roles", "rule_combine_algo"}
            for k, v in rule.items():
                if k not in _known and v:
                    roles_str = _fmt_list(v)
                    break
        return {"order": str(idx + 1), "condition": cond_str, "action": roles_str, "action_type": "role"}

    def _extract_enf_rule(rule: dict[str, Any], idx: int,
                          profile_obj_by_name: dict[str, dict]) -> dict[str, str]:
        conditions = rule.get("conditions") or rule.get("condition") or []
        rule_profiles = (
            rule.get("enforcement_profiles") or rule.get("profiles")
            or rule.get("profile") or []
        )
        if isinstance(rule_profiles, (str, dict)):
            rule_profiles = [rule_profiles]
        cond_str = _fmt_conditions(conditions)
        prof_str = _fmt_list(rule_profiles)
        # Include profile type if we fetched the profile object
        prof_type = ""
        if rule_profiles:
            first_name = _extract_name(rule_profiles[0])
            obj = profile_obj_by_name.get(first_name, {})
            prof_type = obj.get("type") or obj.get("profile_type") or ""
        entry: dict[str, str] = {
            "order": str(idx + 1), "condition": cond_str,
            "action": prof_str, "action_type": "profile",
        }
        if prof_type:
            entry["action_detail"] = prof_type
        return entry

    # ------------------------------------------------------------------
    logger.debug("build_service_tree keys=%s", sorted(service.keys()))
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
    _stage("service", f"Service: {name}", EvaluationStage.SERVICE_MATCH,
           svc_type or None, svc_details)

    # ---- Authentication ----
    auth_method_objs: list[dict] = p.get("auth_methods") or []
    auth_source_objs: list[dict] = p.get("auth_sources") or []
    auth_method_names: list[str] = service.get("authentication_methods") or []
    auth_source_names: list[str] = service.get("authentication_sources") or []

    if auth_method_names or auth_source_names:
        auth_rules: list[dict[str, str]] = []
        for i, obj in enumerate(auth_method_objs or [{}] * len(auth_method_names)):
            n = obj.get("name") or (auth_method_names[i] if i < len(auth_method_names) else f"Method {i+1}")
            t = obj.get("method_type") or obj.get("inner_method") or ""
            auth_rules.append({"order": str(i + 1), "action": n,
                                "action_type": "method", "action_detail": t})
        for i, obj in enumerate(auth_source_objs or [{}] * len(auth_source_names)):
            n = obj.get("name") or (auth_source_names[i] if i < len(auth_source_names) else f"Source {i+1}")
            t = obj.get("type") or obj.get("source_type") or ""
            auth_rules.append({"order": str(len(auth_method_names) + i + 1),
                                "action": n, "action_type": "source", "action_detail": t})
        auth_summary = _fmt_list(auth_method_names) or _fmt_list(auth_source_names)
        _stage("authentication", "Authentication", EvaluationStage.AUTHENTICATION,
               auth_summary or None, {}, policy_rules=auth_rules)

    # ---- Role Mapping ----
    role_policy_name = service.get("role_mapping_policy") or service.get("role_policy") or ""
    role_mapping_obj: dict | None = p.get("role_mapping")
    assigned_roles: list[str] = []

    if role_policy_name:
        rm_rules_raw: list[dict] = (role_mapping_obj.get("rules") or []) if role_mapping_obj else []
        rm_details: dict[str, str] = {"policy": role_policy_name}
        if role_mapping_obj:
            rm_details.update(_policy_details(role_mapping_obj, "rules"))
        policy_rules: list[dict[str, str]] = []
        for i, rule in enumerate(rm_rules_raw):
            entry = _extract_rm_rule(rule, i)
            policy_rules.append(entry)
            for r in entry["action"].split(","):
                r = r.strip()
                if r and r not in assigned_roles:
                    assigned_roles.append(r)

        # Default role
        if role_mapping_obj:
            dr_raw = (
                role_mapping_obj.get("default_role") or role_mapping_obj.get("default_role_name")
                or role_mapping_obj.get("fallback_role") or ""
            )
            if dr_raw:
                dr = _extract_name(dr_raw) if isinstance(dr_raw, dict) else str(dr_raw)
                if dr:
                    policy_rules.append({"order": "default", "condition": "",
                                         "action": dr, "action_type": "default_role"})
                    if dr not in assigned_roles:
                        assigned_roles.append(dr)

        _stage("role_mapping", "Role Mapping", EvaluationStage.ROLE_MAPPING,
               role_policy_name, rm_details, policy_rules=policy_rules)

    # ---- Posture ----
    posture_name = service.get("posture_policy") or ""
    posture_obj: dict | None = p.get("posture_policy")
    if posture_name:
        posture_rules_raw: list[dict] = (posture_obj.get("rules") or []) if posture_obj else []
        posture_details: dict[str, str] = {"policy": posture_name}
        if posture_obj:
            posture_details.update(_policy_details(posture_obj, "rules"))
        pr_rules: list[dict[str, str]] = []
        for i, rule in enumerate(posture_rules_raw):
            cond_str = _fmt_conditions(rule.get("conditions") or rule.get("condition") or [])
            pr_rules.append({"order": str(i + 1), "condition": cond_str,
                              "action": "", "action_type": "posture"})
        _stage("posture", "Posture", EvaluationStage.POSTURE,
               posture_name, posture_details, policy_rules=pr_rules)

    # ---- Enforcement ----
    enforcement_name = (
        service.get("enf_policy") or service.get("enforcement_policy")
        or service.get("enforcement_policy_name") or service.get("enforcement_policies")
        or service.get("enforcement") or ""
    )
    if isinstance(enforcement_name, list):
        enforcement_name = enforcement_name[0] if enforcement_name else ""
    if isinstance(enforcement_name, dict):
        enforcement_name = enforcement_name.get("name") or ""
    enforcement_name = str(enforcement_name).strip()
    logger.debug("enforcement_name resolved to %r", enforcement_name)

    if enforcement_name:
        enforcement_obj: dict | None = p.get("enforcement_policy")
        enf_profile_objs: list[dict] = p.get("enforcement_profiles") or []
        profile_obj_by_name: dict[str, dict] = {
            o.get("name", ""): o for o in enf_profile_objs if o.get("name")
        }
        enf_rules_raw: list[dict] = (enforcement_obj.get("rules") or []) if enforcement_obj else []
        enf_details: dict[str, str] = {"policy": enforcement_name}
        if enforcement_obj:
            enf_details.update(_policy_details(enforcement_obj, "rules"))
        enf_rules_out: list[dict[str, str]] = []
        for i, rule in enumerate(enf_rules_raw):
            enf_rules_out.append(_extract_enf_rule(rule, i, profile_obj_by_name))

        # Default enforcement profile
        if enforcement_obj:
            dp_raw = (
                enforcement_obj.get("default_enforcement_profile")
                or enforcement_obj.get("default_profile") or ""
            )
            if dp_raw:
                dp = _extract_name(dp_raw) if isinstance(dp_raw, dict) else str(dp_raw)
                if dp:
                    enf_rules_out.append({"order": "default", "condition": "",
                                          "action": dp, "action_type": "default_profile"})

        roles_edge_label = f"Roles: {', '.join(assigned_roles)}" if assigned_roles else None
        _stage("enforcement", "Enforcement", EvaluationStage.ENFORCEMENT,
               enforcement_name, enf_details,
               policy_rules=enf_rules_out, edge_label=roles_edge_label)

    # ---- Access Decision ----
    _stage("result", "Access Decision", EvaluationStage.RESULT, None, {})

    return ServiceTree(
        service_id=str(service.get("id", "")),
        service_name=name,
        service_type=svc_type or None,
        nodes=nodes,
        edges=edges,
    )
