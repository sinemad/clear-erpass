import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

import type { DecisionNodeData, EvaluationStage } from "../../types/decisionTree";
import styles from "./DecisionTreeView.module.css";

// ---------------------------------------------------------------------------
// Stage colours
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Start / service header node  (type="decisionNode", default)
// ---------------------------------------------------------------------------

function DecisionNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";

  return (
    <div
      className={`${styles.node} ${selected ? styles.selected : ""}`}
      style={{ borderTopColor: color }}
    >
      <Handle type="target" position={Position.Top} id="top" className={styles.handle} />
      <div className={styles.stageTag} style={{ color }}>{STAGE_LABEL[data.stage] ?? data.stage}</div>
      <div className={styles.label}>{data.label}</div>
      {data.summary && <div className={styles.summary}>{data.summary}</div>}
      <Handle type="source" position={Position.Bottom} id="bottom" className={styles.handle} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Question node  (type="questionNode")
// Displays a humanised condition with Yes→Right and No→Bottom handles.
// ---------------------------------------------------------------------------

function QuestionNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const needsTranslation = data.details?.["needs_translation"] === "true";

  return (
    <div
      className={`${styles.questionNode} ${selected ? styles.questionSelected : ""}`}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Top} id="top" className={styles.handle} />

      {/* Stage label */}
      <div className={styles.questionStageTag} style={{ color }}>
        {STAGE_LABEL[data.stage] ?? data.stage}
      </div>

      {/* Condition question */}
      <div className={styles.questionLabel}>
        {needsTranslation && (
          <span className={styles.xlateWarn} title="Attribute not in translation table — add it to attribute_labels.py">⚠</span>
        )}
        {data.label}
      </div>

      {/* Auth method/source hint */}
      {data.summary && (
        <div className={styles.questionHint}>{data.summary}</div>
      )}

      {/* Yes / No handle labels */}
      <div className={styles.questionHandleLabels}>
        <span className={styles.handleLabelNo}>↓ No</span>
        <span className={styles.handleLabelYes}>Yes →</span>
      </div>

      <Handle type="source" position={Position.Bottom} id="bottom" className={styles.handle} />
      <Handle type="source" position={Position.Right} id="right" className={styles.handleRight} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Outcome node  (type="outcomeNode")
// Displays a role, profile, accept, reject, or default outcome.
// ---------------------------------------------------------------------------

const OUTCOME_META: Record<string, { color: string; icon: string; typeLabel: string }> = {
  role:            { color: "#0891b2", icon: "◉", typeLabel: "Role" },
  default_role:    { color: "#6b7280", icon: "↩", typeLabel: "Default Role" },
  profile:         { color: "#059669", icon: "⇒", typeLabel: "Profile" },
  default_profile: { color: "#6b7280", icon: "↩", typeLabel: "Default Profile" },
  reject:          { color: "#dc2626", icon: "✗", typeLabel: "Reject" },
  accept:          { color: "#059669", icon: "✓", typeLabel: "Accept" },
};

function OutcomeNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const meta = OUTCOME_META[data.summary ?? "role"] ?? OUTCOME_META.role;

  return (
    <div
      className={`${styles.outcomeNode} ${selected ? styles.outcomeSelected : ""}`}
      style={{ borderColor: meta.color, background: `${meta.color}14` }}
    >
      {/* Left handle for Yes-branch incoming edges; Top handle for spine incoming */}
      <Handle type="target" position={Position.Left} id="left" className={styles.handleInvis} />
      <Handle type="target" position={Position.Top} id="top" className={styles.handleInvis} />

      <span className={styles.outcomeIcon} style={{ color: meta.color }}>{meta.icon}</span>
      <div className={styles.outcomeBody}>
        <div className={styles.outcomeTypeLabel} style={{ color: meta.color }}>{meta.typeLabel}</div>
        <div className={styles.outcomeLabel}>{data.label}</div>
      </div>

      {/* Bottom source — all outcome nodes can connect downward */}
      <Handle type="source" position={Position.Bottom} id="bottom" className={styles.handleInvis} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase separator node  (type="phaseNode")
// A thin horizontal rule that acts as a visual merge/join between sections.
// ---------------------------------------------------------------------------

function PhaseNodeComponent({ data }: NodeProps<DecisionNodeData>) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const algo = data.details?.["algo"];
  return (
    <div className={styles.phaseNode} style={{ borderColor: color }}>
      <Handle type="target" position={Position.Top} id="top" className={styles.handleInvis} />
      <div className={styles.phaseLabel} style={{ color }}>
        <span className={styles.phaseArrow}>→</span>
        {data.label}
        {algo && (
          <span className={styles.phaseAlgoBadge}>{algo}</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" className={styles.handleInvis} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node type registry — must be defined outside the component
// ---------------------------------------------------------------------------

const NODE_TYPES = {
  decisionNode: DecisionNodeComponent,
  questionNode: QuestionNodeComponent,
  outcomeNode: OutcomeNodeComponent,
  phaseNode: PhaseNodeComponent,
};

// ---------------------------------------------------------------------------
// Edge style helper — applied when converting raw edges to styled edges
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function styleEdge(edge: any) {
  const label = edge.label as string | undefined;
  const src = (edge.source as string) ?? "";
  const tgt = (edge.target as string) ?? "";

  // Convergence edges — outcomes merging into a phase separator
  const isConvergence =
    !label &&
    (tgt === "rm_sep" || tgt === "enf_sep") &&
    (src.startsWith("rm_out_") || src.startsWith("enf_out_") ||
     src === "rm_default" || src === "enf_default");

  if (isConvergence) {
    return {
      ...edge,
      style: { stroke: "#9ca3af", strokeWidth: 1, strokeDasharray: "3 4" },
      type: "smoothstep",
    };
  }

  // Continuation edges — phase separator → next section
  if (!label && (src === "rm_sep" || src === "enf_sep")) {
    return {
      ...edge,
      style: { stroke: "#9ca3af", strokeWidth: 1.5 },
      type: "straight",
    };
  }

  if (label === "Yes") {
    return {
      ...edge,
      style: { stroke: "#059669", strokeWidth: 2 },
      labelStyle: { fill: "#059669", fontWeight: 700, fontSize: "0.7rem" },
      labelBgStyle: { fill: "var(--color-bg-elevated, #fff)", fillOpacity: 0.9 },
      labelBgPadding: [4, 6] as [number, number],
      labelBgBorderRadius: 4,
    };
  }
  if (label === "No" || label === "No match") {
    return {
      ...edge,
      style: { stroke: "#9ca3af", strokeWidth: 1.5, strokeDasharray: "4 3" },
      labelStyle: { fill: "#9ca3af", fontSize: "0.7rem" },
      labelBgStyle: { fill: "var(--color-bg-elevated, #fff)", fillOpacity: 0.9 },
      labelBgPadding: [4, 6] as [number, number],
      labelBgBorderRadius: 4,
    };
  }
  return edge;
}

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

interface Props {
  nodes: ReturnType<typeof import("reactflow")["useNodesState"]>[0];
  edges: ReturnType<typeof import("reactflow")["useEdgesState"]>[0];
  onNodeClick?: (nodeId: string, data: DecisionNodeData) => void;
}

export default function DecisionTreeView({ nodes, edges, onNodeClick }: Props) {
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.25 }}
      minZoom={0.2}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => onNodeClick?.(node.id, node.data as DecisionNodeData)}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} className={styles.background} />
      <Controls className={styles.controls} />
    </ReactFlow>
  );
}
