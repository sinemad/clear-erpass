import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchServices, type Service } from "../../api/services";
import styles from "./ServicesPage.module.css";

type LoadState = "loading" | "ok" | "unconfigured" | "error";

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
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

  useEffect(() => { load(); }, [load]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Services</h1>
        {loadState === "ok" && (
          <button className={styles.refreshBtn} onClick={load}>Refresh</button>
        )}
      </div>

      {loadState === "loading" && (
        <p className={styles.status}>Loading…</p>
      )}

      {loadState === "unconfigured" && (
        <div className={styles.notice}>
          <p>ClearPass is not configured.</p>
          <button className={styles.linkBtn} onClick={() => navigate("/settings")}>
            Go to Settings →
          </button>
        </div>
      )}

      {loadState === "error" && (
        <div className={styles.notice}>
          <p className={styles.errorMsg}>{errorMsg}</p>
          <button className={styles.refreshBtn} onClick={load}>Retry</button>
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {services.map((svc) => (
              <tr
                key={svc.id}
                className={styles.clickableRow}
                onClick={() => navigate(`/services/${svc.id}`)}
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
                <td className={styles.chevron}>›</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
