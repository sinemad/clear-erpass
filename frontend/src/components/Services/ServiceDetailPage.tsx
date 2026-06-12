import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useNodesState, useEdgesState } from "reactflow";
import { fetchServiceTree } from "../../api/services";
import type { DecisionNodeData, ServiceTree } from "../../types/decisionTree";
import DecisionTreeView from "../DecisionTree/DecisionTreeView";
import styles from "./ServiceDetailPage.module.css";

type LoadState = "loading" | "ok" | "error";

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
            <aside className={styles.detailPanel}>
              <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>{selectedNode.data.label}</span>
                <button
                  className={styles.panelClose}
                  onClick={() => setSelectedNode(null)}
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>

              {selectedNode.data.summary && (
                <p className={styles.panelSummary}>{selectedNode.data.summary}</p>
              )}

              {Object.keys(selectedNode.data.details).length > 0 ? (
                <table className={styles.detailTable}>
                  <tbody>
                    {Object.entries(selectedNode.data.details).map(([k, v]) => (
                      <tr key={k}>
                        <td className={styles.detailKey}>{k}</td>
                        <td className={styles.detailVal}>{v}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className={styles.panelEmpty}>No additional details.</p>
              )}
            </aside>
          )}
        </div>
      )}
    </div>
  );
}
