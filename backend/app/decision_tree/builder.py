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
    """Build a structural ServiceTree from a raw ClearPass service dict.

    Layout philosophy
    -----------------
    The graph is a top-to-bottom pipeline that mirrors how ClearPass evaluates
    a request:

        Service Match
            ↓
        Authentication  ──→ [auth method/source side-nodes]
            ↓
        Role Mapping
            ↓ Rule 1 (inline) … assigns roles
            ↓ Rule 2 (inline)
            ↓ Default Role (inline)
            ↓  "Assigned roles →"
        Enforcement
            ↓ Rule 1 (inline) … applies profile  ──→ [profile side-node]
            ↓ Rule 2 (inline)                    ──→ [profile side-node]
            ↓ Default Profile (inline)           ──→ [profile side-node]
            ↓
        Access Decision

    Main pipeline and inline rule nodes sit at x=0 (single column).
    Supplementary side-nodes (auth options, enforcement profiles) sit at
    x=_SIDE_X so they don't interrupt the vertical read.
    """
    p = policies or {}
    nodes: list[DecisionNode] = []
    edges: list[DecisionEdge] = []
    edge_order = 0
    prev_id: str | None = None   # last node in the main vertical flow
    current_y = 0

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _pipe(node_id: str, label: str, stage: EvaluationStage,
              summary: str | None, details: dict[str, str],
              edge_label: str | None = None) -> None:
        """Add a main pipeline node and connect it from the previous node."""
        nonlocal prev_id, edge_order, current_y
        nodes.append(DecisionNode(
            id=node_id,
            position=Position(x=_MAIN_X, y=current_y),
            data=DecisionNodeData(label=label, stage=stage,
                                  status=EvaluationStatus.NOT_EVALUATED,
                                  summary=summary, details=details),
        ))
        if prev_id:
            edge_order += 1
            edges.append(DecisionEdge(
                id=f"e{edge_order}", source=prev_id, target=node_id,
                order=edge_order, animated=False, label=edge_label,
            ))
        prev_id = node_id
        current_y += _STAGE_H

    def _rule(node_id: str, label: str, stage: EvaluationStage,
              details: dict[str, str]) -> None:
        """Add an inline rule node in the main vertical flow."""
        nonlocal prev_id, edge_order, current_y
        nodes.append(DecisionNode(
            id=node_id, type="inlineRuleNode",
            position=Position(x=_MAIN_X, y=current_y),
            data=DecisionNodeData(label=label, stage=stage,
                                  status=EvaluationStatus.NOT_EVALUATED,
                                  summary=None, details=details),
        ))
        edge_order += 1
        edges.append(DecisionEdge(
            id=f"e{edge_order}", source=prev_id, target=node_id,
            order=edge_order, animated=False,
        ))
        prev_id = node_id
        current_y += _RULE_H

    def _side(node_id: str, parent_id: str, label: str, stage: EvaluationStage,
              summary: str | None, details: dict[str, str],
              side_y: int, node_type: str = "policyRuleNode") -> None:
        """Add a supplementary side-node connected from parent (no effect on current_y)."""
        nonlocal edge_order
        nodes.append(DecisionNode(
            id=node_id, type=node_type,
            position=Position(x=_SIDE_X, y=side_y),
            data=DecisionNodeData(label=label, stage=stage,
                                  status=EvaluationStatus.NOT_EVALUATED,
                                  summary=summary, details=details),
        ))
        edge_order += 1
        edges.append(DecisionEdge(
            id=f"e{edge_order}", source=parent_id, target=node_id,
            order=edge_order, animated=False,
        ))

    def _gap() -> None:
        nonlocal current_y
        current_y += _SECTION_GAP

    # ------------------------------------------------------------------

    logger.debug("build_service_tree keys=%s", sorted(service.keys()))

    name = service.get("name", "Unknown Service")
    svc_type = str(service.get("type") or "")

    # ---- Service Match -----------------------------------------------
    svc_details: dict[str, str] = {}
    if svc_type:
        svc_details["type"] = svc_type
    if service.get("template"):
        svc_details["template"] = str(service["template"])
    if service.get("description"):
        svc_details["description"] = str(service["description"])
    _pipe("service", f"Service: {name}", EvaluationStage.SERVICE_MATCH,
          svc_type or None, svc_details)
    _gap()

    # ---- Authentication (side-nodes only — methods are options, not steps)
    auth_method_objs: list[dict] = p.get("auth_methods") or []
    auth_source_objs: list[dict] = p.get("auth_sources") or []
    auth_method_names: list[str] = service.get("authentication_methods") or []
    auth_source_names: list[str] = service.get("authentication_sources") or []

    if auth_method_names or auth_source_names:
        auth_summary = _fmt_list(auth_method_names) or _fmt_list(auth_source_names)
        _pipe("authentication", "Authentication", EvaluationStage.AUTHENTICATION,
              auth_summary or None, {})
        side_y = current_y - _STAGE_H  # align side-nodes with the auth main node
        all_auth_items = list(zip(
            auth_method_objs or [{}] * len(auth_method_names),
            auth_method_names or [""] * len(auth_method_objs),
            ["method"] * max(len(auth_method_objs), len(auth_method_names)),
        )) + list(zip(
            auth_source_objs or [{}] * len(auth_source_names),
            auth_source_names or [""] * len(auth_source_objs),
            ["source"] * max(len(auth_source_objs), len(auth_source_names)),
        ))
        for idx, (obj, fallback_name, kind) in enumerate(all_auth_items):
            a_name = obj.get("name") or fallback_name or f"Auth {idx+1}"
            a_type = obj.get("method_type") or obj.get("type") or obj.get("source_type") or ""
            stage = EvaluationStage.AUTHENTICATION if kind == "method" else EvaluationStage.AUTHORIZATION
            _side(f"auth_{kind}_{idx}", "authentication", a_name, stage,
                  a_type or None, _policy_details(obj) if obj else {}, side_y + idx * 85)
        _gap()

    # ---- Role Mapping -----------------------------------------------
    role_policy_name = service.get("role_mapping_policy") or service.get("role_policy") or ""
    role_mapping_obj: dict | None = p.get("role_mapping")
    assigned_roles: list[str] = []   # collected to label the edge into Enforcement

    if role_policy_name:
        rm_rules: list[dict] = (role_mapping_obj.get("rules") or []) if role_mapping_obj else []
        rm_details: dict[str, str] = {"policy": role_policy_name}
        if role_mapping_obj:
            rm_details.update(_policy_details(role_mapping_obj, "rules"))
        _pipe("role_mapping", "Role Mapping", EvaluationStage.ROLE_MAPPING,
              role_policy_name, rm_details)

        for i, rule in enumerate(rm_rules):
            logger.debug("role_mapping rule[%d] keys=%s", i, list(rule.keys()))
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

            if roles_str:
                for r in roles_str.split(","):
                    r = r.strip()
                    if r and r not in assigned_roles:
                        assigned_roles.append(r)

            rd: dict[str, str] = {"Order": str(i + 1)}
            if cond_str:
                rd["conditions"] = cond_str
            if roles_str:
                rd["roles"] = roles_str
            _rule(f"rm_rule_{i}", cond_str or f"Rule {i + 1}",
                  EvaluationStage.ROLE_MAPPING, rd)

        # Default role (policy-level fallback)
        if role_mapping_obj:
            default_role = (
                role_mapping_obj.get("default_role") or role_mapping_obj.get("default_role_name")
                or role_mapping_obj.get("fallback_role") or ""
            )
            if default_role:
                dr = _extract_name(default_role) if isinstance(default_role, dict) else str(default_role)
                if dr and dr not in assigned_roles:
                    assigned_roles.append(dr)
                _rule("rm_default", "Default (no match)",
                      EvaluationStage.ROLE_MAPPING,
                      {"roles": dr, "note": "Applied when no rule matches"})
        _gap()

    # ---- Posture -----------------------------------------------
    posture_name = service.get("posture_policy") or ""
    posture_obj: dict | None = p.get("posture_policy")
    if posture_name:
        posture_rules: list[dict] = (posture_obj.get("rules") or []) if posture_obj else []
        posture_details: dict[str, str] = {"policy": posture_name}
        if posture_obj:
            posture_details.update(_policy_details(posture_obj, "rules"))
        _pipe("posture", "Posture", EvaluationStage.POSTURE, posture_name, posture_details)
        for i, rule in enumerate(posture_rules):
            cond_str = _fmt_conditions(rule.get("conditions") or rule.get("condition") or [])
            pd: dict[str, str] = {"Order": str(i + 1)}
            if cond_str:
                pd["conditions"] = cond_str
            _rule(f"posture_rule_{i}", cond_str or f"Rule {i + 1}",
                  EvaluationStage.POSTURE, pd)
        _gap()

    # ---- Enforcement -----------------------------------------------
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

    enforcement_obj: dict | None = p.get("enforcement_policy")
    enf_profile_objs: list[dict] = p.get("enforcement_profiles") or []
    profile_obj_by_name: dict[str, dict] = {
        obj.get("name", ""): obj for obj in enf_profile_objs if obj.get("name")
    }

    if enforcement_name:
        enf_rules: list[dict] = (enforcement_obj.get("rules") or []) if enforcement_obj else []
        enf_details: dict[str, str] = {"policy": enforcement_name}
        if enforcement_obj:
            enf_details.update(_policy_details(enforcement_obj, "rules"))

        # Edge label shows what roles are flowing in from role mapping
        roles_edge_label = (
            f"Roles: {', '.join(assigned_roles)}" if assigned_roles else None
        )
        _pipe("enforcement", "Enforcement", EvaluationStage.ENFORCEMENT,
              enforcement_name, enf_details, edge_label=roles_edge_label)

        side_y = current_y - _STAGE_H   # start side-nodes aligned with enforcement
        seen_profiles: set[str] = set()

        for i, rule in enumerate(enf_rules):
            conditions = rule.get("conditions") or rule.get("condition") or []
            rule_profiles = (
                rule.get("enforcement_profiles") or rule.get("profiles")
                or rule.get("profile") or []
            )
            if isinstance(rule_profiles, (str, dict)):
                rule_profiles = [rule_profiles]

            cond_str = _fmt_conditions(conditions)
            prof_str = _fmt_list(rule_profiles)

            ed: dict[str, str] = {"Order": str(i + 1)}
            if cond_str:
                ed["conditions"] = cond_str
            if prof_str:
                ed["profiles"] = prof_str
            rule_node_id = f"enf_rule_{i}"
            _rule(rule_node_id, cond_str or f"Rule {i + 1}",
                  EvaluationStage.ENFORCEMENT, ed)

            # Enforcement profile as side-node connected from this rule
            for rp in rule_profiles:
                prof_name = _extract_name(rp)
                if not prof_name or prof_name in seen_profiles:
                    continue
                seen_profiles.add(prof_name)
                prof_obj = profile_obj_by_name.get(prof_name, {})
                prof_type = prof_obj.get("type") or prof_obj.get("profile_type") or ""
                prof_details = _policy_details(prof_obj) if prof_obj else {}
                _side(f"enf_profile_{prof_name.replace(' ', '_')}",
                      rule_node_id, prof_name,
                      EvaluationStage.ENFORCEMENT,
                      prof_type or None, prof_details,
                      side_y, node_type="enfProfileNode")
                side_y += 85

        # Default enforcement profile
        if enforcement_obj:
            default_prof = (
                enforcement_obj.get("default_enforcement_profile")
                or enforcement_obj.get("default_profile") or ""
            )
            if default_prof:
                dp = _extract_name(default_prof) if isinstance(default_prof, dict) else str(default_prof)
                if dp:
                    _rule("enf_default", "Default (no match)",
                          EvaluationStage.ENFORCEMENT,
                          {"profiles": dp, "note": "Applied when no rule matches"})
                    if dp not in seen_profiles:
                        dp_obj = profile_obj_by_name.get(dp, {})
                        dp_type = dp_obj.get("type") or dp_obj.get("profile_type") or ""
                        _side(f"enf_profile_{dp.replace(' ', '_')}",
                              "enf_default", dp,
                              EvaluationStage.ENFORCEMENT,
                              dp_type or None,
                              _policy_details(dp_obj) if dp_obj else {},
                              side_y, node_type="enfProfileNode")
        _gap()

    # ---- Access Decision -------------------------------------------
    _pipe("result", "Access Decision", EvaluationStage.RESULT, None, {})

    return ServiceTree(
        service_id=str(service.get("id", "")),
        service_name=name,
        service_type=svc_type or None,
        nodes=nodes,
        edges=edges,
    )
