import { useCallback, useEffect, useRef, useState } from "react";
import { fetchLogs, type LogEntry, type LogLevel } from "../../api/logs";
import styles from "./LogsPage.module.css";

const LEVEL_OPTIONS: Array<{ value: "" | LogLevel; label: string }> = [
  { value: "", label: "All levels" },
  { value: "DEBUG", label: "DEBUG+" },
  { value: "INFO", label: "INFO+" },
  { value: "WARNING", label: "WARNING+" },
  { value: "ERROR", label: "ERROR+" },
];

const POLL_INTERVAL_MS = 3000;

export default function LogsPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [levelFilter, setLevelFilter] = useState<"" | LogLevel>("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(() => {
    fetchLogs(200, levelFilter || undefined)
      .then((data) => {
        setEntries(data);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }, [levelFilter]);

  // Scroll to bottom when entries update and autoScroll is on
  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, autoScroll]);

  // Polling
  useEffect(() => {
    load();
    if (autoRefresh) {
      intervalRef.current = setInterval(load, POLL_INTERVAL_MS);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load, autoRefresh]);

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <h1 className={styles.title}>Logs</h1>

        <select
          className={styles.select}
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value as "" | LogLevel)}
          aria-label="Filter by level"
        >
          {LEVEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          Auto-refresh
        </label>

        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>

        <button className={styles.clearBtn} onClick={() => setEntries([])}>
          Clear
        </button>

        {!autoRefresh && (
          <button className={styles.refreshBtn} onClick={load}>
            Refresh
          </button>
        )}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.logArea}>
        {entries.length === 0 ? (
          <p className={styles.empty}>No log entries yet.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.colTime}>Time</th>
                <th className={styles.colLevel}>Level</th>
                <th className={styles.colLogger}>Logger</th>
                <th className={styles.colMessage}>Message</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => (
                <tr key={i} className={styles[`row${entry.level}` as keyof typeof styles]}>
                  <td className={styles.colTime}>{entry.timestamp}</td>
                  <td className={styles.colLevel}>
                    <span className={`${styles.badge} ${styles[`badge${entry.level}` as keyof typeof styles]}`}>
                      {entry.level}
                    </span>
                  </td>
                  <td className={styles.colLogger}>{entry.logger}</td>
                  <td className={styles.colMessage}>{entry.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div ref={bottomRef} />
      </div>

      <p className={styles.footer}>
        {entries.length} entr{entries.length === 1 ? "y" : "ies"} · buffer holds last 500
        {autoRefresh && <span> · refreshing every {POLL_INTERVAL_MS / 1000}s</span>}
      </p>
    </div>
  );
}
