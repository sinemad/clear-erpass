import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchServices, type Service } from "../../api/services";
import {
  fetchAccessTrackerByService,
  type AccessTrackerRecord,
} from "../../api/access_tracker";
import styles from "./ServicesPage.module.css";

type LoadState = "loading" | "ok" | "unconfigured" | "error";
type ATLoadState = "idle" | "loading" | "ok" | "error" | "unimplemented";

// ── Result badge ──────────────────────────────────────────────────────────────

function ResultBadge({ result }: { result: string }) {
  const r = result.toUpperCase();
  const cls =
    r === "ACCEPT"
      ? styles.resultAccept
      : r === "REJECT"
      ? styles.resultReject
      : styles.resultDrop;
  return <span className={`${styles.resultBadge} ${cls}`}>{result}</span>;
}

// ── AT Drawer ─────────────────────────────────────────────────────────────────

function AccessTrackerDrawer({
  service,
  open,
  onToggle,
  onViewTree,
}: {
  service: Service;
  open: boolean;
  onToggle: () => void;
  onViewTree: () => void;
}) {
  const [records, setRecords] = useState<AccessTrackerRecord[]>([]);
  const [loadState, setLoadState] = useState<ATLoadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const load = useCallback(() => {
    if (!service.name) return;
    setLoadState("loading");
    fetchAccessTrackerByService(service.name)
      .then((data) => {
        setRecords(data);
        setLoadState("ok");
      })
      .catch((err: Error & { status?: number }) => {
        if (err.status === 501) {
          setLoadState("unimplemented");
        } else {
          setErrorMsg(err.message);
          setLoadState("error");
        }
      });
  }, [service.name]);

  useEffect(() => {
    setRecords([]);
    setLoadState("idle");
    if (open) load();
  }, [service.name, open, load]);

  function formatTime(iso: string) {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  return (
    <aside className={`${styles.drawer} ${open ? styles.drawerOpen : styles.drawerClosed}`}>
      {/* Toggle handle */}
      <button
        className={styles.drawerHandle}
        onClick={onToggle}
        aria-label={open ? "Collapse activity drawer" : "Expand activity drawer"}
        title={open ? "Collapse" : "Access Tracker"}
      >
        <span className={styles.drawerHandleLabel}>Access Tracker</span>
        <span className={styles.drawerHandleChevron}>{open ? "›" : "‹"}</span>
      </button>

      {open && (
        <div className={styles.drawerContent}>
          {/* Drawer header */}
          <div className={styles.drawerHeader}>
            <div className={styles.drawerTitle}>
              <span className={styles.drawerServiceName}>{service.name}</span>
              <span className={styles.drawerSubtitle}>Recent Activity</span>
            </div>
            <div className={styles.drawerActions}>
              <button className={styles.viewTreeBtn} onClick={onViewTree}>
                Policy Tree →
              </button>
              <button
                className={styles.drawerRefreshBtn}
                onClick={load}
                aria-label="Refresh"
                title="Refresh"
              >
                ↺
              </button>
            </div>
          </div>

          {/* Body */}
          <div className={styles.drawerBody}>
            {loadState === "loading" && (
              <p className={styles.drawerStatus}>Loading…</p>
            )}

            {loadState === "unimplemented" && (
              <p className={styles.drawerStatus}>
                Access Tracker API not yet implemented.
              </p>
            )}

            {loadState === "error" && (
              <div className={styles.drawerError}>
                <p>{errorMsg}</p>
                <button onClick={load}>Retry</button>
              </div>
            )}

            {loadState === "ok" && records.length === 0 && (
              <p className={styles.drawerStatus}>No records found.</p>
            )}

            {loadState === "ok" && records.length > 0 && (
              <ul className={styles.atList}>
                {records.map((rec) => (
                  <li key={rec.id} className={styles.atItem}>
                    <div className={styles.atRow}>
                      <span className={styles.atTime}>{formatTime(rec.timestamp)}</span>
                      <ResultBadge result={rec.result} />
                    </div>
                    {rec.username && (
                      <div className={styles.atMeta}>
                        <span className={styles.atMetaLabel}>User</span>
                        <span className={styles.atMetaVal}>{rec.username}</span>
                      </div>
                    )}
                    {rec.endpoint_mac && (
                      <div className={styles.atMeta}>
                        <span className={styles.atMetaLabel}>MAC</span>
                        <span className={styles.atMetaVal}>{rec.endpoint_mac}</span>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setLoadState("loading");
    fetchServices()
      .then((data) => {
        setServices(data);
        setLoadState("ok");
      })
      .catch((err: Error & { status?: number }) => {
        if (err.status === 503) {
          setLoadState("unconfigured");
        } else {
          setErrorMsg(err.message);
          setLoadState("error");
        }
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleRowClick(svc: Service) {
    setSelectedService((prev) => {
      if (prev?.id === svc.id) return null;
      return svc;
    });
    setDrawerOpen(true);
  }

  return (
    <div className={styles.page}>
      {/* Top header */}
      <div className={styles.header}>
        <h1>Services</h1>
        {loadState === "ok" && (
          <button className={styles.refreshBtn} onClick={load}>
            Refresh
          </button>
        )}
      </div>

      {/* Body: service list + optional drawer */}
      <div className={styles.body}>
        <div className={styles.listPanel}>
          {loadState === "loading" && (
            <p className={styles.status}>Loading…</p>
          )}

          {loadState === "unconfigured" && (
            <div className={styles.notice}>
              <p>ClearPass is not configured.</p>
              <button
                className={styles.linkBtn}
                onClick={() => navigate("/settings")}
              >
                Go to Settings →
              </button>
            </div>
          )}

          {loadState === "error" && (
            <div className={styles.notice}>
              <p className={styles.errorMsg}>{errorMsg}</p>
              <button className={styles.refreshBtn} onClick={load}>
                Retry
              </button>
            </div>
          )}

          {loadState === "ok" && services.length === 0 && (
            <p className={styles.status}>No services found.</p>
          )}

          {loadState === "ok" && services.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc) => (
                  <tr
                    key={svc.id}
                    className={`${styles.clickableRow} ${
                      selectedService?.id === svc.id ? styles.selectedRow : ""
                    }`}
                    onClick={() => handleRowClick(svc)}
                  >
                    <td className={styles.nameCell}>{svc.name}</td>
                    <td>{svc.type ?? "—"}</td>
                    <td>
                      {svc.enabled === undefined ? (
                        "—"
                      ) : svc.enabled ? (
                        <span className={styles.badgeEnabled}>Enabled</span>
                      ) : (
                        <span className={styles.badgeDisabled}>Disabled</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {selectedService && (
          <AccessTrackerDrawer
            service={selectedService}
            open={drawerOpen}
            onToggle={() => setDrawerOpen((v) => !v)}
            onViewTree={() => navigate(`/services/${selectedService.id}`)}
          />
        )}
      </div>
    </div>
  );
}
