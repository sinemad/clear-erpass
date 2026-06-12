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


from app.decision_tree.attribute_labels import make_question_label


def build_service_tree(service: dict[str, Any], policies: dict[str, Any] | None = None) -> ServiceTree:
    """Build a binary decision tree for a ClearPass service.

    Layout
    ------
    The graph is a vertical decision tree:
    - Question nodes (conditions) are on the left spine (x=0), stacked top-to-bottom.
    - "Yes / matched" outcomes branch to the RIGHT (x=_OUT_X) at the same y.
    - "No / no match" edges continue DOWN the spine to the next question.
    - Default/fallback outcomes appear on the spine when no rule matches.
    - The Access Decision (Accept) sits at the bottom of the spine.
    """
    p = policies or {}
    nodes: list[DecisionNode] = []
    edges: list[DecisionEdge] = []
    _ec = 0
    current_y = 0

    _Q_X = 0       # question/spine x
    _OUT_X = 420   # yes-branch outcome x
    _Y_STEP = 160  # vertical step between spine nodes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _edge(src: str, tgt: str, label: str | None = None,
              src_handle: str | None = None) -> DecisionEdge:
        nonlocal _ec
        _ec += 1
        return DecisionEdge(
            id=f"e{_ec}", source=src, target=tgt,
            order=_ec, animated=False, label=label,
            sourceHandle=src_handle,
        )

    def _question(nid: str, label: str, stage: EvaluationStage,
                  raw_cond: str | None = None, needs_xlat: bool = False,
                  summary: str | None = None) -> DecisionNode:
        d: dict[str, str] = {}
        if raw_cond:
            d["condition"] = raw_cond
        if needs_xlat:
            d["needs_translation"] = "true"
        return DecisionNode(
            id=nid, type="questionNode",
            position=Position(x=_Q_X, y=current_y),
            data=DecisionNodeData(
                label=label, stage=stage, summary=summary,
                status=EvaluationStatus.NOT_EVALUATED, details=d,
            ),
        )

    def _outcome(nid: str, label: str, stage: EvaluationStage,
                 outcome_type: str, x: float | None = None,
                 y: float | None = None) -> DecisionNode:
        return DecisionNode(
            id=nid, type="outcomeNode",
            position=Position(x=x if x is not None else _OUT_X,
                              y=y if y is not None else current_y),
            data=DecisionNodeData(
                label=label, stage=stage,
                status=EvaluationStatus.NOT_EVALUATED,
                summary=outcome_type, details={},
            ),
        )

    # ------------------------------------------------------------------
    logger.debug("build_service_tree keys=%s", sorted(service.keys()))
    name = service.get("name", "Unknown Service")
    svc_type = str(service.get("type") or "")

    # ── Service header (start node, not a question) ────────────────────
    svc_details: dict[str, str] = {}
    if svc_type:
        svc_details["type"] = svc_type
    if service.get("description"):
        svc_details["description"] = str(service["description"])
    nodes.append(DecisionNode(
        id="start",
        position=Position(x=_Q_X, y=current_y),
        data=DecisionNodeData(
            label=name, stage=EvaluationStage.SERVICE_MATCH,
            status=EvaluationStatus.NOT_EVALUATED,
            summary=svc_type or None, details=svc_details,
        ),
    ))
    prev_spine = "start"
    current_y += _Y_STEP

    # ── Authentication ─────────────────────────────────────────────────
    auth_method_names: list[str] = service.get("authentication_methods") or []
    auth_source_names: list[str] = service.get("authentication_sources") or []

    if auth_method_names or auth_source_names:
        methods = _fmt_list(auth_method_names) or _fmt_list(auth_source_names)
        q = _question("auth_q", "Authentication successful?",
                      EvaluationStage.AUTHENTICATION, summary=methods or None)
        nodes.append(q)
        edges.append(_edge(prev_spine, "auth_q"))

        # Auth fail → Reject outcome on the right
        nodes.append(_outcome("auth_reject", "Reject",
                              EvaluationStage.AUTHENTICATION, "reject"))
        edges.append(_edge("auth_q", "auth_reject", label="No", src_handle="right"))

        prev_spine = "auth_q"
        current_y += _Y_STEP

    # ── Role Mapping ───────────────────────────────────────────────────
    role_policy_name = service.get("role_mapping_policy") or service.get("role_policy") or ""
    role_mapping_obj: dict | None = p.get("role_mapping")
    assigned_roles: list[str] = []

    role_yes_out_ids: list[str] = []  # Yes-branch role outcomes — also connect to enforcement

    if role_policy_name:
        rm_rules: list[dict] = (role_mapping_obj.get("rules") or []) if role_mapping_obj else []

        last_rm_q: str = prev_spine

        for i, rule in enumerate(rm_rules):
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
                _skip = {"id", "conditions", "condition", "roles", "role", "role_name",
                         "role_names", "assigned_roles", "rule_combine_algo"}
                for k, v in rule.items():
                    if k not in _skip and v:
                        roles_str = _fmt_list(v)
                        break

            q_label, needs_xlat = make_question_label(cond_str) if cond_str else (f"Rule {i + 1}?", False)
            qid = f"rm_q_{i}"
            nodes.append(_question(qid, q_label, EvaluationStage.ROLE_MAPPING,
                                   raw_cond=cond_str, needs_xlat=needs_xlat))

            if i == 0:
                edges.append(_edge(prev_spine, qid,
                                   src_handle="bottom" if prev_spine == "auth_q" else None))
            else:
                edges.append(_edge(f"rm_q_{i - 1}", qid, label="No", src_handle="bottom"))

            # Yes → role outcome (right side)
            if roles_str:
                oid = f"rm_out_{i}"
                nodes.append(_outcome(oid, roles_str, EvaluationStage.ROLE_MAPPING, "role"))
                edges.append(_edge(qid, oid, label="Yes", src_handle="right"))
                role_yes_out_ids.append(oid)
                for r in roles_str.split(","):
                    r = r.strip()
                    if r and r not in assigned_roles:
                        assigned_roles.append(r)

            last_rm_q = qid
            current_y += _Y_STEP

        # Default role — sits on the spine (passthrough to enforcement)
        dr_raw = (role_mapping_obj or {}).get("default_role") or \
                 (role_mapping_obj or {}).get("default_role_name") or \
                 (role_mapping_obj or {}).get("fallback_role")
        if dr_raw:
            dr = _extract_name(dr_raw) if isinstance(dr_raw, dict) else str(dr_raw)
            if dr:
                nodes.append(_outcome("rm_default", dr, EvaluationStage.ROLE_MAPPING,
                                      "default_role", x=_Q_X))
                edges.append(_edge(last_rm_q, "rm_default",
                                   label="No match" if rm_rules else None,
                                   src_handle="bottom" if rm_rules else None))
                if dr not in assigned_roles:
                    assigned_roles.append(dr)
                prev_spine = "rm_default"
                current_y += _Y_STEP
        else:
            prev_spine = last_rm_q if rm_rules else prev_spine

    # ── Enforcement ────────────────────────────────────────────────────
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
        enf_rules: list[dict] = (enforcement_obj.get("rules") or []) if enforcement_obj else []

        last_enf_q: str = prev_spine

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

            q_label, needs_xlat = make_question_label(cond_str) if cond_str else (f"Rule {i + 1}?", False)
            qid = f"enf_q_{i}"
            nodes.append(_question(qid, q_label, EvaluationStage.ENFORCEMENT,
                                   raw_cond=cond_str, needs_xlat=needs_xlat))

            if i == 0:
                edges.append(_edge(prev_spine, qid,
                                   src_handle="bottom" if prev_spine in ("auth_q",) else None))
                # All role Yes-branch outcomes also converge here — enforcement always runs
                for rid in role_yes_out_ids:
                    edges.append(_edge(rid, qid, src_handle="bottom"))
            else:
                edges.append(_edge(f"enf_q_{i - 1}", qid, label="No", src_handle="bottom"))

            if prof_str:
                oid = f"enf_out_{i}"
                nodes.append(_outcome(oid, prof_str, EvaluationStage.ENFORCEMENT, "profile"))
                edges.append(_edge(qid, oid, label="Yes", src_handle="right"))

            last_enf_q = qid
            current_y += _Y_STEP

        # Default enforcement profile — on the spine
        dp_raw = (enforcement_obj or {}).get("default_enforcement_profile") or \
                 (enforcement_obj or {}).get("default_profile")
        if dp_raw:
            dp = _extract_name(dp_raw) if isinstance(dp_raw, dict) else str(dp_raw)
            if dp:
                nodes.append(_outcome("enf_default", dp, EvaluationStage.ENFORCEMENT,
                                      "default_profile", x=_Q_X))
                edges.append(_edge(last_enf_q, "enf_default",
                                   label="No match" if enf_rules else None,
                                   src_handle="bottom" if enf_rules else None))
                prev_spine = "enf_default"
                current_y += _Y_STEP
        else:
            prev_spine = last_enf_q if enf_rules else prev_spine

    # ── Access Decision ────────────────────────────────────────────────
    nodes.append(_outcome("result", "Access: Accept",
                          EvaluationStage.RESULT, "accept", x=_Q_X))
    edges.append(_edge(prev_spine, "result"))

    return ServiceTree(
        service_id=str(service.get("id", "")),
        service_name=name,
        service_type=svc_type or None,
        nodes=nodes,
        edges=edges,
    )
