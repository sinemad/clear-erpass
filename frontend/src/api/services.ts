import type { ServiceTree } from "../types/decisionTree";

export interface Service {
  id: number | string;
  name: string;
  type?: string;
  description?: string;
  enabled?: boolean;
  [key: string]: unknown;
}

export async function fetchServiceTree(serviceId: string | number): Promise<ServiceTree> {
  const res = await fetch(`/api/services/${serviceId}/decision-tree`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return res.json();
}

export async function fetchServices(): Promise<Service[]> {
  const res = await fetch("/api/services");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return res.json();
}
