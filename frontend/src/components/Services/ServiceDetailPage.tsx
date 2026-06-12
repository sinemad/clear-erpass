import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useNodesState, useEdgesState } from "reactflow";
import { fetchServiceTree } from "../../api/services";
import type { DecisionNodeData, EvaluationStage, PolicyRule, ServiceTree } from "../../types/decisionTree";
import DecisionTreeView from "../DecisionTree/DecisionTreeView";
import styles from "./ServiceDetailPage.module.css";

type LoadState = "loading" | "ok" | "error";

// -------------------------------------------------------------------------
// Stage metadata
// -------------------------------------------------------------------------

const STAGE_COLOR: Record<EvaluationStage, string> = {
  service_match: "#7c3aed",
  authentication: "#2563eb",
  authorization: "#4f46e5",
  role_mapping: "#0891b2",
  posture: "#d97706",
  enforcement: "#059669",
  result: "#6b7280",
};

const STAGE_LABEL: Record<EvaluationStage, string> = {
  service_match: "Service",
  authentication: "Auth",
  authorization: "Authz",
  role_mapping: "Role Mapping",
  posture: "Posture",
  enforcement: "Enforcement",
  result: "Result",
};

const STAGE_ICON: Record<EvaluationStage, string> = {
  service_match: "◈",
  authentication: "⚿",
  authorization: "⊕",
  role_mapping: "⊜",
  posture: "⊛",
  enforcement: "⇒",
  result: "✓",
};

// -------------------------------------------------------------------------
// Condition helpers
// -------------------------------------------------------------------------

const OPERATORS = [
  "NOT_EQUALS", "EQUALS", "CONTAINS", "STARTS_WITH", "ENDS_WITH",
  "MATCHES_REGEX", "GREATER_THAN", "LESS_THAN",
];

const OP_DISPLAY: Record<string, string> = {
  EQUALS: "=", NOT_EQUALS: "≠", CONTAINS: "∋",
  STARTS_WITH: "^=", ENDS_WITH: "$=",
  MATCHES_REGEX: "~", GREATER_THAN: ">", LESS_THAN: "<",
};

function ConditionCell({ value }: { value: string }) {
  if (!value) return <span className={styles.condEmpty}>—</span>;

  const parts = value.replace(/ \(\+\d+ more\)$/, "").split(" AND ");
  const extra = value.match(/\(\+\d+ more\)/)?.[0];

  return (
    <div className={styles.conditionBlock}>
      {parts.map((part, i) => {
        for (const op of OPERATORS) {
          const idx = part.indexOf(` ${op} `);
          if (idx !== -1) {
            const attr = part.slice(0, idx);
            const val = part.slice(idx + op.length + 2);
            return (
              <div key={i} className={styles.conditionRow}>
                <span className={styles.condAttr}>{attr}</span>
                <span className={styles.condOp}>{OP_DISPLAY[op] ?? op}</span>
                <span className={styles.condVal}>{val}</span>
              </div>
            );
          }
        }
        return (
          <div key={i} className={styles.conditionRow}>
            <span className={styles.condAttr}>{part}</span>
          </div>
        );
      })}
      {extra && <div className={styles.condMore}>{extra}</div>}
    </div>
  );
}

// -------------------------------------------------------------------------
// Action cell — chips for roles/profiles, plain text for methods/sources
// -------------------------------------------------------------------------

const ACTION_COLOR: Record<string, string> = {
  role: "#0891b2",
  default_role: "#6b7280",
  profile: "#059669",
  default_profile: "#6b7280",
  method: "#7c3aed",
  source: "#2563eb",
  posture: "#d97706",
};

const ACTION_LABEL: Record<string, string> = {
  role: "Role",
  default_role: "Default Role",
  profile: "Profile",
  default_profile: "Default Profile",
  method: "Method",
  source: "Source",
  posture: "Check",
};

function ActionCell({ rule, stageColor }: { rule: PolicyRule; stageColor: string }) {
  const color = ACTION_COLOR[rule.action_type] ?? stageColor;
  const isDefault = rule.action_type === "default_role" || rule.action_type === "default_profile";

  if (!rule.action) {
    return <span className={styles.condEmpty}>—</span>;
  }

  const items = rule.action.split(",").map((s) => s.trim()).filter(Boolean);

  return (
    <div className={styles.actionCell}>
      {items.map((item) => (
        <span
          key={item}
          className={`${styles.chip} ${isDefault ? styles.chipDefault : ""}`}
          style={{ borderColor: color, color }}
          title={item}
        >
          {item}
        </span>
      ))}
      {rule.action_detail && (
        <span className={styles.actionDetail}>{rule.action_detail}</span>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------
// Rule table
// -------------------------------------------------------------------------

function RuleTable({ rules, stage }: { rules: PolicyRule[]; stage: EvaluationStage }) {
  const color = STAGE_COLOR[stage] ?? "#6b7280";

  // Determine which columns to show
  const hasConditions = rules.some((r) => r.condition);
  const actionLabel = rules.length > 0 ? (ACTION_LABEL[rules[0].action_type] ?? "Action") : "Action";

  return (
    <div className={styles.ruleTableWrapper}>
      <table className={styles.ruleTable}>
        <thead>
          <tr>
            <th className={styles.ruleTableTh} style={{ width: "2rem" }}>#</th>
            {hasConditions && <th className={styles.ruleTableTh}>Condition</th>}
            <th className={styles.ruleTableTh}>{actionLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule) => {
            const isDefault = rule.action_type === "default_role" || rule.action_type === "default_profile";
            return (
              <tr
                key={rule.order}
                className={`${styles.ruleTableRow} ${isDefault ? styles.ruleTableRowDefault : ""}`}
              >
                <td className={styles.ruleTableTd}>
                  {isDefault ? (
                    <span className={styles.defaultBadge} title="Applied when no rule matches">↩</span>
                  ) : (
                    <span className={styles.ruleNum} style={{ color }}>{rule.order}</span>
                  )}
                </td>
                {hasConditions && (
                  <td className={styles.ruleTableTd}>
                    <ConditionCell value={rule.condition ?? ""} />
                  </td>
                )}
                <td className={styles.ruleTableTd}>
                  <ActionCell rule={rule} stageColor={color} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// -------------------------------------------------------------------------
// Detail panel — shown when a stage node is clicked
// -------------------------------------------------------------------------

const FIELD_ICON: Record<string, string> = {
  policy: "◈",
  type: "◧",
  template: "⊞",
  description: "≡",
  method_type: "⚿",
  inner_method: "⟳",
  source_type: "⊕",
};

function DetailPanel({
  data,
  onClose,
}: {
  data: DecisionNodeData;
  onClose: () => void;
}) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const details = data.details as Record<string, string>;
  const policyRules = data.policy_rules ?? [];

  // Show only non-redundant "other" fields (skip policy if it's in the label)
  const skipKeys = new Set(["Order", "rules_count"]);
  const otherEntries = Object.entries(details).filter(([k]) => !skipKeys.has(k));

  return (
    <aside className={styles.detailPanel}>
      {/* Header */}
      <div className={styles.panelHeader} style={{ borderTopColor: color }}>
        <div className={styles.panelHeaderLeft}>
          <span className={styles.stageBadge} style={{ background: `${color}20`, color }}>
            <span className={styles.stageIcon}>{STAGE_ICON[data.stage]}</span>
            {STAGE_LABEL[data.stage]}
          </span>
        </div>
        <button className={styles.panelClose} onClick={onClose} aria-label="Close">✕</button>
      </div>

      {/* Label */}
      <div className={styles.panelLabel}>{data.label}</div>

      {/* Summary (policy name) */}
      {data.summary && (
        <p className={styles.panelSummary}>{data.summary}</p>
      )}

      {/* Other metadata fields (type, template, description, etc.) */}
      {otherEntries.length > 0 && (
        <div className={styles.panelSection}>
          {otherEntries.map(([k, v]) => (
            <div key={k} className={styles.fieldRow}>
              <span className={styles.fieldIcon}>{FIELD_ICON[k] ?? "›"}</span>
              <span className={styles.fieldVal}>{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* Rule table */}
      {policyRules.length > 0 && (
        <div className={styles.panelSection}>
          <div className={styles.sectionLabel}>
            <span className={styles.sectionIcon}>≡</span>
            Rules ({policyRules.filter((r) => r.order !== "default").length})
          </div>
          <RuleTable rules={policyRules} stage={data.stage} />
        </div>
      )}

      {policyRules.length === 0 && otherEntries.length === 0 && !data.summary && (
        <p className={styles.panelEmpty}>No additional details.</p>
      )}
    </aside>
  );
}

// -------------------------------------------------------------------------
// Page
// -------------------------------------------------------------------------

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [tree, setTree] = useState<ServiceTree | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [selectedNode, setSelectedNode] = useState<{ id: string; data: DecisionNodeData } | null>(null);

  const [nodes, setNodes] = useNodesState([]);
  const [edges, setEdges] = useEdgesState([]);

  const load = useCallback(() => {
    if (!id) return;
    setLoadState("loading");
    fetchServiceTree(id)
      .then((data) => {
        setTree(data);
        setNodes(data.nodes);
        setEdges(data.edges);
        setLoadState("ok");
      })
      .catch((err: Error) => {
        setErrorMsg(err.message);
        setLoadState("error");
      });
  }, [id, setNodes, setEdges]);

  useEffect(() => { load(); }, [load]);

  const handleNodeClick = useCallback((nodeId: string, nodeData: DecisionNodeData) => {
    setSelectedNode((prev) => prev?.id === nodeId ? null : { id: nodeId, data: nodeData });
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={() => navigate("/services")}>
          ← Services
        </button>
        {tree && (
          <>
            <span className={styles.serviceName}>{tree.service_name}</span>
            {tree.service_type && (
              <span className={styles.typeTag}>{tree.service_type}</span>
            )}
          </>
        )}
        {loadState === "loading" && <span className={styles.loading}>Loading…</span>}
      </div>

      {loadState === "error" && (
        <div className={styles.errorBanner}>
          {errorMsg}
          <button onClick={load}>Retry</button>
        </div>
      )}

      {loadState === "ok" && (
        <div className={styles.body}>
          <div className={styles.flowContainer}>
            <DecisionTreeView
              nodes={nodes}
              edges={edges}
              onNodeClick={handleNodeClick}
            />
          </div>

          {selectedNode && (
            <DetailPanel
              data={selectedNode.data}
              onClose={() => setSelectedNode(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
