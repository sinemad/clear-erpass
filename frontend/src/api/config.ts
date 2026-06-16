export interface ConfigRead {
  clearpass_base_url: string | null;
  clearpass_client_id: string | null;
  clearpass_client_secret_configured: boolean;
  clearpass_verify_ssl: boolean;
  debug_logging: boolean;
}

export interface ConfigUpdate {
  clearpass_base_url: string;
  clearpass_client_id: string;
  clearpass_client_secret?: string;
  clearpass_verify_ssl: boolean;
  debug_logging: boolean;
}

export async function fetchConfig(): Promise<ConfigRead> {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error(`Failed to load config: ${res.status}`);
  return res.json();
}

export async function saveConfig(body: ConfigUpdate): Promise<ConfigRead> {
  const res = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save config: ${res.status}`);
  return res.json();
}
