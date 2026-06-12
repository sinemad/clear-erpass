import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

import type { DecisionNodeData, EvaluationStage, EvaluationStatus } from "../../types/decisionTree";
import styles from "./DecisionTreeView.module.css";

// ---------------------------------------------------------------------------
// Stage metadata
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
  service_match: "Service Match",
  authentication: "Authentication",
  authorization: "Authorization",
  role_mapping: "Role Mapping",
  posture: "Posture",
  enforcement: "Enforcement",
  result: "Result",
};

function resolvedColor(stage: EvaluationStage, status: EvaluationStatus): string {
  if (stage === "result") {
    if (status === "passed" || status === "matched") return "#059669";
    if (status === "failed" || status === "not_matched" || status === "error") return "#dc2626";
  }
  return STAGE_COLOR[stage] ?? "#6b7280";
}

// ---------------------------------------------------------------------------
// Custom node component
// ---------------------------------------------------------------------------

function DecisionNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = resolvedColor(data.stage, data.status);
  const isStructural = data.status === "not_evaluated";

  return (
    <div
      className={`${styles.node} ${isStructural ? styles.structural : styles.evaluated} ${selected ? styles.selected : ""}`}
      style={{ borderTopColor: color }}
    >
      <Handle type="target" position={Position.Top} className={styles.handle} />

      <div className={styles.stageTag} style={{ color }}>
        {STAGE_LABEL[data.stage] ?? data.stage}
      </div>
      <div className={styles.label}>{data.label}</div>
      {data.summary && <div className={styles.summary}>{data.summary}</div>}

      <Handle type="source" position={Position.Bottom} className={styles.handle} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Condition label — parses "Attr OPERATOR Value" into styled spans
// ---------------------------------------------------------------------------

const OPERATORS = [
  "NOT_EQUALS", "EQUALS", "CONTAINS", "STARTS_WITH", "ENDS_WITH",
  "MATCHES_REGEX", "GREATER_THAN", "LESS_THAN",
];

const OP_SYMBOL: Record<string, string> = {
  EQUALS: "=", NOT_EQUALS: "≠", CONTAINS: "∋",
  STARTS_WITH: "^=", ENDS_WITH: "$=",
  MATCHES_REGEX: "~", GREATER_THAN: ">", LESS_THAN: "<",
};

function ConditionLabel({ text }: { text: string }) {
  for (const op of OPERATORS) {
    const idx = text.indexOf(` ${op} `);
    if (idx !== -1) {
      const attr = text.slice(0, idx);
      const val = text.slice(idx + op.length + 2);
      return (
        <span className={styles.condLabel}>
          <span className={styles.condLabelAttr}>{attr}</span>
          <span className={styles.condLabelOp}>{OP_SYMBOL[op] ?? op}</span>
          <span className={styles.condLabelVal}>{val}</span>
        </span>
      );
    }
  }
  return <span>{text}</span>;
}

// ---------------------------------------------------------------------------
// Policy rule sub-node component
// ---------------------------------------------------------------------------

const CHIP_COLOR: Record<string, string> = {
  roles: "#0891b2",
  profiles: "#059669",
};

function PolicyRuleNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const details = data.details as Record<string, string>;
  const order = details?.["Order"];
  const roles = details?.["roles"];
  const profiles = details?.["profiles"];
  const outcomeField = roles ? "roles" : profiles ? "profiles" : null;
  const outcomeValue = roles ?? profiles ?? null;

  return (
    <div
      className={`${styles.ruleNode} ${selected ? styles.selected : ""}`}
      style={{ borderLeftColor: color }}
    >
      <Handle type="target" position={Position.Left} className={styles.handle} />

      {order && <div className={styles.ruleOrder}>Rule {order}</div>}
      <div className={styles.ruleLabel}>
        <ConditionLabel text={data.label} />
      </div>

      {outcomeValue && outcomeField ? (
        <div className={styles.nodeChipRow}>
          {outcomeValue.split(",").map((s) => s.trim()).filter(Boolean).map((item) => (
            <span
              key={item}
              className={styles.nodeChip}
              style={{ color: CHIP_COLOR[outcomeField], borderColor: CHIP_COLOR[outcomeField] }}
              title={item}
            >
              {item}
            </span>
          ))}
        </div>
      ) : (
        data.summary && <div className={styles.ruleSummary}>{data.summary}</div>
      )}

      <Handle type="source" position={Position.Right} className={styles.handle} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline rule node — sits in the main vertical flow between stage nodes
// ---------------------------------------------------------------------------

function InlineRuleNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = STAGE_COLOR[data.stage] ?? "#6b7280";
  const details = data.details as Record<string, string>;
  const order = details?.["Order"];
  const roles = details?.["roles"];
  const profiles = details?.["profiles"];
  const outcomeField = roles ? "roles" : profiles ? "profiles" : null;
  const outcomeValue = roles ?? profiles ?? null;

  return (
    <div
      className={`${styles.inlineRule} ${selected ? styles.selected : ""}`}
      style={{ borderLeftColor: color }}
    >
      <Handle type="target" position={Position.Top} className={styles.handle} />

      {order && <div className={styles.ruleOrder} style={{ color }}>{`Rule ${order}`}</div>}
      <div className={styles.inlineRuleLabel}>
        <ConditionLabel text={data.label} />
      </div>

      {outcomeValue && outcomeField && (
        <div className={styles.nodeChipRow}>
          {outcomeValue.split(",").map((s) => s.trim()).filter(Boolean).map((item) => (
            <span
              key={item}
              className={styles.nodeChip}
              style={{ color: CHIP_COLOR[outcomeField], borderColor: CHIP_COLOR[outcomeField] }}
              title={item}
            >
              {item}
            </span>
          ))}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className={styles.handle} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Enforcement profile output node
// ---------------------------------------------------------------------------

function EnfProfileNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const color = "#059669"; // enforcement green

  return (
    <div
      className={`${styles.profileNode} ${selected ? styles.selected : ""}`}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className={styles.handle} />

      <div className={styles.profileTag} style={{ color }}>⇒ Profile</div>
      <div className={styles.profileLabel}>{data.label}</div>
      {data.summary && <div className={styles.profileType}>{data.summary}</div>}
    </div>
  );
}

// Must be defined outside the component to avoid re-creating on each render.
const NODE_TYPES = {
  decisionNode: DecisionNodeComponent,
  policyRuleNode: PolicyRuleNodeComponent,
  inlineRuleNode: InlineRuleNodeComponent,
  enfProfileNode: EnfProfileNodeComponent,
};

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
      fitViewOptions={{ padding: 0.3 }}
      minZoom={0.25}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => onNodeClick?.(node.id, node.data as DecisionNodeData)}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} className={styles.background} />
      <Controls className={styles.controls} />
    </ReactFlow>
  );
}
