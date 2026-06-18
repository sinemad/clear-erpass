export interface AccessTrackerRecord {
  id: string;
  timestamp: string;
  service_name: string;
  username: string | null;
  endpoint_mac: string | null;
  ip_address: string | null;
  auth_status: string;  // ACCEPT | REJECT | TIMEOUT | DROP | ERROR
}

export interface AccessTrackerDetail {
  id: string;
  timestamp: string;
  service_name: string;
  username: string | null;
  endpoint_mac: string | null;
  ip_address: string | null;
  auth_status: string;
  auth_method: string | null;
  auth_source: string | null;
  roles: string[];
  enforcement_profiles: string[];
  error_code: number | null;
  error_message: string | null;
}

async function _fetch<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return res.json();
}

export function fetchAccessTrackerByService(
  serviceName: string,
  limit = 50
): Promise<AccessTrackerRecord[]> {
  const params = new URLSearchParams({ service_name: serviceName, limit: String(limit) });
  return _fetch(`/api/access-tracker?${params}`);
}

export function fetchAccessTrackerRecord(id: string): Promise<AccessTrackerDetail> {
  return _fetch(`/api/access-tracker/${id}`);
}
