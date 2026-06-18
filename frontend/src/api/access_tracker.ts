export interface AccessTrackerRecord {
  id: string;
  timestamp: string;
  service_name: string;
  username: string | null;
  endpoint_mac: string | null;
  result: string;
}

export async function fetchAccessTrackerByService(
  serviceName: string,
  limit = 50
): Promise<AccessTrackerRecord[]> {
  const params = new URLSearchParams({ service_name: serviceName, limit: String(limit) });
  const res = await fetch(`/api/access-tracker?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return res.json();
}
