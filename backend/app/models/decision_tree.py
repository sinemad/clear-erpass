"""
Decision tree domain models.

These models represent the data shape returned by the backend API for the
"Decision Tree" view of an Access Tracker record. They are intentionally
modeled to map cleanly onto React Flow's `Node` / `Edge` types on the
frontend (see frontend/src/types/decisionTree.ts).

Design notes
------------
- `DecisionNode` carries both the React-Flow-required fields (id, position,
  type, data) AND ClearPass-specific metadata (stage, status, details) inside
  `data`. Position can be computed server-side (e.g. via a simple layered
  layout) or left as (0, 0) and laid out client-side with a library like
  dagre/elkjs — start server-side for simplicity, revisit if layouts get
  complex.
- `DecisionEdge` includes an `order` field so the frontend can animate edges
  in the correct sequence regardless of the order they appear in the list.
- `DecisionTree.path` is the ordered list of node IDs that were actually
  traversed for this specific Access Tracker record — this is what drives
  the step-by-step animation. Nodes/edges NOT in `path` are rendered dimmed.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EvaluationStage(str, Enum):
    """High-level ClearPass policy evaluation stages.

    Used to pick the React Flow custom node renderer on the frontend and to
    group/color nodes consistently.
    """

    SERVICE_MATCH = "service_match"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ROLE_MAPPING = "role_mapping"
    POSTURE = "posture"
    ENFORCEMENT = "enforcement"
    RESULT = "result"


class EvaluationStatus(str, Enum):
    """Outcome of a single evaluation step.

    `not_evaluated` covers nodes that exist in the service's policy
    definition but were never reached for this particular request (e.g. an
    enforcement profile rule that didn't match). These are rendered dimmed
    and excluded from `DecisionTree.path`.
    """

    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"
    ERROR = "error"


class Position(BaseModel):
    """X/Y coordinates, mirrors React Flow's `XYPosition`."""

    x: float
    y: float


class DecisionNodeData(BaseModel):
    """The `data` payload attached to a React Flow node.

    Anything ClearPass-specific (rule text, attribute values, timestamps)
    lives here rather than on the top-level node, keeping the top-level
    shape generic/React-Flow-friendly.
    """

    label: str = Field(..., description="Short display label, e.g. 'Role Mapping: Contractor'")
    stage: EvaluationStage
    status: EvaluationStatus
    summary: str | None = Field(
        default=None,
        description="One-line human-readable summary, e.g. 'Matched rule 3: AD-Group contains VPN-Users'",
    )
    details: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Raw key/value detail pairs from ClearPass for this step "
            "(e.g. policy name, rule number, attribute checked, value seen). "
            "Rendered in a side panel / tooltip when the node is selected."
        ),
    )
    policy_rules: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Ordered list of policy rules for this stage. Each entry has: "
            "order, condition (optional), action, action_type "
            "(role|profile|default_role|default_profile|method|source). "
            "Rendered as a rule table in the drawer."
        ),
    )
    timestamp: datetime | None = Field(
        default=None,
        description="When this step was evaluated, if available from ClearPass.",
    )


class DecisionNode(BaseModel):
    """A single node in the decision tree, mirrors React Flow's `Node` type."""

    id: str
    type: str = Field(
        default="decisionNode",
        description="React Flow custom node type name to render this node with.",
    )
    position: Position = Field(default_factory=lambda: Position(x=0, y=0))
    data: DecisionNodeData


class DecisionEdge(BaseModel):
    """A single edge in the decision tree, mirrors React Flow's `Edge` type."""

    id: str
    source: str
    target: str
    label: str | None = Field(
        default=None,
        description="Optional edge label, e.g. 'matched' / 'no match -> next rule'",
    )
    order: int = Field(
        ...,
        description=(
            "Sequence position of this edge within the overall evaluation "
            "flow, used to drive the step-by-step animation. Lower = earlier."
        ),
    )
    animated: bool = Field(
        default=False,
        description="Whether this edge is on the actual traversal path for this record.",
    )


class ServiceTree(BaseModel):
    """Structural decision tree derived from a ClearPass service definition.

    Unlike DecisionTree (which represents a specific Access Tracker record
    traversal), ServiceTree is a static blueprint of the policy stages
    configured for the service. All nodes carry status=NOT_EVALUATED because
    no specific request has been evaluated — the tree shows what *could*
    happen, not what *did* happen.
    """

    service_id: str
    service_name: str
    service_type: str | None = None
    nodes: list[DecisionNode]
    edges: list[DecisionEdge]


class DecisionTree(BaseModel):
    """Full decision tree for a single Access Tracker record.

    Returned by e.g. `GET /api/access-tracker/{record_id}/decision-tree`.
    """

    record_id: str = Field(..., description="ClearPass Access Tracker record ID")
    service_name: str
    request_timestamp: datetime
    final_result: EvaluationStatus

    nodes: list[DecisionNode]
    edges: list[DecisionEdge]

    path: list[str] = Field(
        ...,
        description=(
            "Ordered list of node IDs representing the actual evaluation "
            "path taken for this record. Drives step-by-step animation; "
            "nodes not in this list are rendered dimmed/inactive."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "R00000123-01",
                "service_name": "Wireless 802.1X",
                "request_timestamp": "2026-06-12T14:32:01Z",
                "final_result": "passed",
                "nodes": [
                    {
                        "id": "service_match",
                        "type": "decisionNode",
                        "position": {"x": 0, "y": 0},
                        "data": {
                            "label": "Service: Wireless 802.1X",
                            "stage": "service_match",
                            "status": "matched",
                            "summary": "Request matched service categorization rules",
                            "details": {"service_category": "RADIUS_802_1X_WIRELESS"},
                        },
                    },
                    {
                        "id": "auth_eap_peap",
                        "type": "decisionNode",
                        "position": {"x": 0, "y": 150},
                        "data": {
                            "label": "Authentication: EAP-PEAP",
                            "stage": "authentication",
                            "status": "passed",
                            "summary": "EAP-PEAP authentication against AD",
                            "details": {"method": "EAP-PEAP", "source": "Active Directory"},
                        },
                    },
                    {
                        "id": "role_mapping_contractor",
                        "type": "decisionNode",
                        "position": {"x": 0, "y": 300},
                        "data": {
                            "label": "Role Mapping: Contractor",
                            "stage": "role_mapping",
                            "status": "matched",
                            "summary": "Matched rule 3: AD-Group contains 'Contractors'",
                            "details": {"rule": "3", "attribute": "AD-Group", "value": "Contractors"},
                        },
                    },
                    {
                        "id": "enforcement_contractor_vlan",
                        "type": "decisionNode",
                        "position": {"x": 0, "y": 450},
                        "data": {
                            "label": "Enforcement: Contractor VLAN",
                            "stage": "enforcement",
                            "status": "matched",
                            "summary": "Applied 'Contractor VLAN 20' enforcement profile",
                            "details": {"profile": "Contractor VLAN 20", "vlan": "20"},
                        },
                    },
                    {
                        "id": "result_accept",
                        "type": "decisionNode",
                        "position": {"x": 0, "y": 600},
                        "data": {
                            "label": "Result: ACCEPT",
                            "stage": "result",
                            "status": "passed",
                            "summary": "Access-Accept sent",
                            "details": {},
                        },
                    },
                ],
                "edges": [
                    {"id": "e1", "source": "service_match", "target": "auth_eap_peap", "order": 1, "animated": True},
                    {"id": "e2", "source": "auth_eap_peap", "target": "role_mapping_contractor", "order": 2, "animated": True},
                    {"id": "e3", "source": "role_mapping_contractor", "target": "enforcement_contractor_vlan", "order": 3, "animated": True},
                    {"id": "e4", "source": "enforcement_contractor_vlan", "target": "result_accept", "order": 4, "animated": True},
                ],
                "path": [
                    "service_match",
                    "auth_eap_peap",
                    "role_mapping_contractor",
                    "enforcement_contractor_vlan",
                    "result_accept",
                ],
            }
        }
