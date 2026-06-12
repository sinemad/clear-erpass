import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useNodesState, useEdgesState } from "reactflow";
import { fetchServiceTree } from "../../api/services";
import type { DecisionNodeData, EvaluationStage, ServiceTree } from "../../types/decisionTree";
import DecisionTreeView, { styleEdge } from "../DecisionTree/DecisionTreeView";
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
  const rawCondition = details["condition"];
  const needsTranslation = details["needs_translation"] === "true";
  const algo = details["algo"];

  // Fields to show in the info section (skip internal keys)
  const skipKeys = new Set(["condition", "needs_translation", "algo"]);
  const infoEntries = Object.entries(details).filter(([k]) => !skipKeys.has(k));

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

      {/* Node label */}
      <div className={styles.panelLabel}>{data.label}</div>

      {/* Summary line (service type, auth method hint, etc.) */}
      {data.summary && !["role", "default_role", "profile", "default_profile", "accept", "reject"].includes(data.summary) && (
        <p className={styles.panelSummary}>{data.summary}</p>
      )}

      {/* Evaluation mode badge */}
      {algo && (
        <p className={styles.panelSummary}>
          <span className={styles.algoLine}>Evaluation: {algo}</span>
        </p>
      )}

      {/* Raw condition for question nodes */}
      {rawCondition && (
        <div className={styles.panelSection}>
          <div className={styles.sectionLabel}>
            <span className={styles.sectionIcon}>≡</span> Condition
            {needsTranslation && (
              <span className={styles.xlateFlag} title="Add this attribute to attribute_labels.py in the backend">⚠ needs translation</span>
            )}
          </div>
          <ConditionCell value={rawCondition} />
        </div>
      )}

      {/* Info fields (type, description, etc.) */}
      {infoEntries.length > 0 && (
        <div className={styles.panelSection}>
          {infoEntries.map(([k, v]) => (
            <div key={k} className={styles.fieldRow}>
              <span className={styles.fieldIcon}>{FIELD_ICON[k] ?? "›"}</span>
              <span className={styles.fieldVal}>{v}</span>
            </div>
          ))}
        </div>
      )}

      {!rawCondition && infoEntries.length === 0 && !data.summary && (
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
        // Apply Yes/No visual styling to edges
        setEdges(data.edges.map(styleEdge) as typeof data.edges);
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
