/**
 * Decision tree types.
 *
 * These mirror the backend Pydantic models in
 * backend/app/models/decision_tree.py and map directly onto React Flow's
 * `Node<T>` / `Edge<T>` generic types.
 *
 * If/when an OpenAPI-generated client is introduced (e.g. via
 * `openapi-typescript`), these can be replaced by the generated types --
 * keep this file as the canonical hand-written reference in the meantime.
 */

import type { Node, Edge } from "reactflow";

/** High-level ClearPass policy evaluation stages. */
export type EvaluationStage =
  | "service_match"
  | "authentication"
  | "authorization"
  | "role_mapping"
  | "posture"
  | "enforcement"
  | "result";

/** Outcome of a single evaluation step. */
export type EvaluationStatus =
  | "matched"
  | "not_matched"
  | "passed"
  | "failed"
  | "not_evaluated"
  | "error";

/**
 * Data payload attached to each decision tree node.
 * Corresponds to `DecisionNodeData` in the backend.
 */
export interface DecisionNodeData {
  label: string;
  stage: EvaluationStage;
  status: EvaluationStatus;
  /** One-line human-readable summary, e.g. "Matched rule 3: AD-Group contains VPN-Users" */
  summary?: string;
  /** Raw key/value detail pairs shown in a side panel/tooltip when selected. */
  details: Record<string, string>;
  /** ISO 8601 timestamp, if available. */
  timestamp?: string;
}

/**
 * A single decision tree node.
 * Corresponds to `DecisionNode` in the backend; extends React Flow's `Node`.
 */
export type DecisionNode = Node<DecisionNodeData>;

/**
 * A single decision tree edge.
 * Corresponds to `DecisionEdge` in the backend; extends React Flow's `Edge`.
 *
 * `order` and `animated` are used by the playback controller to step through
 * the traversal path in sequence.
 */
export type DecisionEdge = Edge<{ order: number }> & {
  /** Sequence position within the overall evaluation flow (lower = earlier). */
  order: number;
  /** Whether this edge is on the actual traversal path for this record. */
  animated: boolean;
};

/**
 * Full decision tree response for a single Access Tracker record.
 * Corresponds to `DecisionTree` in the backend.
 *
 * Returned by `GET /api/access-tracker/{recordId}/decision-tree`.
 */
export interface DecisionTree {
  recordId: string;
  serviceName: string;
  /** ISO 8601 timestamp of the original request. */
  requestTimestamp: string;
  finalResult: EvaluationStatus;

  nodes: DecisionNode[];
  edges: DecisionEdge[];

  /**
   * Ordered list of node IDs representing the actual evaluation path taken
   * for this record. Drives step-by-step animation; nodes not in this list
   * should be rendered dimmed/inactive.
   */
  path: string[];
}

/**
 * Playback state for the animated decision tree view.
 * Purely a frontend concept -- not part of the API response.
 */
export interface DecisionTreePlaybackState {
  /** Index into `DecisionTree.path` representing the current step. -1 = not started. */
  currentStepIndex: number;
  isPlaying: boolean;
  /** Milliseconds between automatic steps when playing. */
  stepIntervalMs: number;
}
