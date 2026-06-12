import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useNodesState, useEdgesState } from "reactflow";
import { fetchServiceTree } from "../../api/services";
import type { DecisionNodeData, EvaluationStage, ServiceTree } from "../../types/decisionTree";
import DecisionTreeView from "../DecisionTree/DecisionTreeView";
import styles from "./ServiceDetailPage.module.css";

type LoadState = "loading" | "ok" | "error";

// -------------------------------------------------------------------------
// Stage metadata for the drawer header badge
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
// Chip-type fields: rendered as pill chips instead of plain text
// -------------------------------------------------------------------------
const CHIP_FIELDS = new Set(["roles", "profiles"]);

// Fields rendered in a code block (monospace, condition expressions)
const CODE_FIELDS = new Set(["conditions"]);

// Fields rendered with a named icon prefix
const FIELD_ICON: Record<string, string> = {
  policy: "◈",
  type: "◧",
  template: "⊞",
  description: "≡",
  method_type: "⚿",
  inner_method: "⟳",
  source_type: "⊕",
};

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------

function Chips({ value, color }: { value: string; color: string }) {
  const items = value.split(",").map((s) => s.trim()).filter(Boolean);
  return (
    <div className={styles.chipRow}>
      {items.map((item) => (
        <span key={item} className={styles.chip} style={{ borderColor: color, color }}>
          {item}
        </span>
      ))}
    </div>
  );
}

function ConditionBlock({ value }: { value: string }) {
  // Try to parse "Attr OPERATOR Value" segments separated by " AND "
  const parts = value.replace(/ \(\+\d+ more\)$/, "").split(" AND ");
  return (
    <div className={styles.conditionBlock}>
      {parts.map((part, i) => {
        const ops = ["NOT_EQUALS", "EQUALS", "CONTAINS", "STARTS_WITH", "ENDS_WITH", "MATCHES_REGEX", "GREATER_THAN", "LESS_THAN"];
        let matched = false;
        for (const op of ops) {
          const idx = part.indexOf(` ${op} `);
          if (idx !== -1) {
            const attr = part.slice(0, idx);
            const val = part.slice(idx + op.length + 2);
            const opDisplay = op === "NOT_EQUALS" ? "≠" : op === "EQUALS" ? "=" : op === "CONTAINS" ? "∋" : op === "STARTS_WITH" ? "^=" : op === "ENDS_WITH" ? "$=" : op === "GREATER_THAN" ? ">" : op === "LESS_THAN" ? "<" : op;
            matched = true;
            return (
              <div key={i} className={styles.conditionRow}>
                <span className={styles.condAttr}>{attr}</span>
                <span className={styles.condOp}>{opDisplay}</span>
                <span className={styles.condVal}>{val}</span>
              </div>
            );
          }
        }
        return matched ? null : (
          <div key={i} className={styles.conditionRow}>
            <span className={styles.condAttr}>{part}</span>
          </div>
        );
      })}
      {value.includes("(+") && (
        <div className={styles.condMore}>{value.match(/\(\+\d+ more\)/)?.[0]}</div>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------
// Main panel
// -------------------------------------------------------------------------

function DetailPanel({
  data,
  onClose,
}: {
  data: DecisionNodeData;
  onClose: () => void;
}) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const details = data.details as Record<string, string>;
  const order = details["Order"];

  // Partition details into sections
  const chipEntries = Object.entries(details).filter(([k]) => CHIP_FIELDS.has(k));
  const codeEntries = Object.entries(details).filter(([k]) => CODE_FIELDS.has(k));
  const otherEntries = Object.entries(details).filter(
    ([k]) => !CHIP_FIELDS.has(k) && !CODE_FIELDS.has(k) && k !== "Order"
  );

  return (
    <aside className={styles.detailPanel}>
      {/* Header */}
      <div className={styles.panelHeader} style={{ borderTopColor: color }}>
        <div className={styles.panelHeaderLeft}>
          <span className={styles.stageBadge} style={{ background: `${color}20`, color }}>
            <span className={styles.stageIcon}>{STAGE_ICON[data.stage]}</span>
            {STAGE_LABEL[data.stage]}
          </span>
          {order && <span className={styles.orderBadge}>Rule {order}</span>}
        </div>
        <button className={styles.panelClose} onClick={onClose} aria-label="Close">✕</button>
      </div>

      {/* Label */}
      <div className={styles.panelLabel}>{data.label}</div>

      {/* Summary */}
      {data.summary && !chipEntries.find(([k]) => k === "roles" || k === "profiles") && (
        <p className={styles.panelSummary}>{data.summary}</p>
      )}

      {/* Chips: roles */}
      {chipEntries.filter(([k]) => k === "roles").map(([, v]) => (
        <div key="roles" className={styles.panelSection}>
          <div className={styles.sectionLabel}>
            <span className={styles.sectionIcon}>◉</span> Roles
          </div>
          <Chips value={v} color="#0891b2" />
        </div>
      ))}

      {/* Chips: profiles */}
      {chipEntries.filter(([k]) => k === "profiles").map(([, v]) => (
        <div key="profiles" className={styles.panelSection}>
          <div className={styles.sectionLabel}>
            <span className={styles.sectionIcon}>⇒</span> Profiles
          </div>
          <Chips value={v} color="#059669" />
        </div>
      ))}

      {/* Conditions */}
      {codeEntries.map(([, v]) => (
        <div key="conditions" className={styles.panelSection}>
          <div className={styles.sectionLabel}>
            <span className={styles.sectionIcon}>≡</span> Condition
          </div>
          <ConditionBlock value={v} />
        </div>
      ))}

      {/* Other fields */}
      {otherEntries.length > 0 && (
        <div className={styles.panelSection}>
          {otherEntries.map(([k, v]) => (
            <div key={k} className={styles.fieldRow}>
              <span className={styles.fieldIcon}>{FIELD_ICON[k] ?? "·"}</span>
              <span className={styles.fieldVal}>{v}</span>
            </div>
          ))}
        </div>
      )}

      {Object.keys(details).filter((k) => k !== "Order").length === 0 && (
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

  const handleNodeClick = useCallback((nodeId: string, data: DecisionNodeData) => {
    setSelectedNode((prev) => prev?.id === nodeId ? null : { id: nodeId, data });
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
