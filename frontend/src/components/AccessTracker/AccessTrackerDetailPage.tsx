import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchAccessTrackerRecord, type AccessTrackerDetail } from "../../api/access_tracker";
import styles from "./AccessTrackerDetailPage.module.css";

type LoadState = "loading" | "ok" | "error";

function StatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();
  const cls =
    s === "ACCEPT"
      ? styles.statusAccept
      : s === "REJECT" || s === "ERROR"
      ? styles.statusReject
      : styles.statusDrop;
  return <span className={`${styles.statusBadge} ${cls}`}>{status}</span>;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value && value !== 0) return null;
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{value}</span>
    </div>
  );
}

function ChipList({ values }: { values: string[] }) {
  if (!values.length) return <span className={styles.fieldMuted}>—</span>;
  return (
    <div className={styles.chipList}>
      {values.map((v) => (
        <span key={v} className={styles.chip}>{v}</span>
      ))}
    </div>
  );
}

export default function AccessTrackerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [record, setRecord] = useState<AccessTrackerDetail | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    setLoadState("loading");
    fetchAccessTrackerRecord(id)
      .then((data) => {
        setRecord(data);
        setLoadState("ok");
      })
      .catch((err: Error) => {
        setErrorMsg(err.message);
        setLoadState("error");
      });
  }, [id]);

  useEffect(() => { load(); }, [load]);

  function formatTime(iso: string) {
    try {
      return new Date(iso).toLocaleString(undefined, {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short",
      });
    } catch {
      return iso;
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={() => navigate(-1)}>
          ← Back
        </button>
        {record && (
          <>
            <span className={styles.title}>Access Tracker</span>
            <StatusBadge status={record.auth_status} />
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

      {loadState === "ok" && record && (
        <div className={styles.body}>
          {/* ── Identity ───────────────────────────────────────────────── */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Identity</h2>
            <div className={styles.fields}>
              <Field label="Username" value={record.username ?? "—"} />
              <Field label="MAC Address" value={record.endpoint_mac ?? "—"} />
              <Field label="IP Address" value={record.ip_address ?? "—"} />
              <Field label="Timestamp" value={formatTime(record.timestamp)} />
            </div>
          </section>

          {/* ── Service & Authentication ────────────────────────────────── */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Authentication</h2>
            <div className={styles.fields}>
              <Field label="Service" value={record.service_name} />
              <Field label="Method" value={record.auth_method ?? "—"} />
              <Field label="Source" value={record.auth_source ?? "—"} />
              <Field label="Result" value={<StatusBadge status={record.auth_status} />} />
            </div>
          </section>

          {/* ── Authorization ───────────────────────────────────────────── */}
          {(record.roles.length > 0 || record.enforcement_profiles.length > 0) && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Authorization</h2>
              <div className={styles.fields}>
                {record.roles.length > 0 && (
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Roles</span>
                    <ChipList values={record.roles} />
                  </div>
                )}
                {record.enforcement_profiles.length > 0 && (
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Enforcement Profiles</span>
                    <ChipList values={record.enforcement_profiles} />
                  </div>
                )}
              </div>
            </section>
          )}

          {/* ── Error (if present) ──────────────────────────────────────── */}
          {(record.error_code != null || record.error_message) && (
            <section className={`${styles.section} ${styles.sectionError}`}>
              <h2 className={styles.sectionTitle}>Error</h2>
              <div className={styles.fields}>
                {record.error_code != null && (
                  <Field label="Code" value={String(record.error_code)} />
                )}
                {record.error_message && (
                  <Field label="Message" value={record.error_message} />
                )}
              </div>
            </section>
          )}

          <div className={styles.recordId}>Record ID: {record.id}</div>
        </div>
      )}
    </div>
  );
}
