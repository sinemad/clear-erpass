export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  logger: string;
  message: string;
}

export async function fetchLogs(limit = 200, level?: LogLevel): Promise<LogEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (level) params.set("level", level);
  const res = await fetch(`/api/logs?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`);
  return res.json();
}
