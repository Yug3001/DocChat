import { Dataset, Mutation } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDatasetsList(): Promise<{datasets: Dataset[]}> {
  const res = await fetch(`${BASE}/api/dataset/list`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch datasets list");
  }
  return res.json();
}

export async function uploadCsvDataset(file: File, displayName: string): Promise<{dataset_id: string, message: string}> {
  const form = new FormData();
  form.append("file", file);
  form.append("display_name", displayName);

  const res = await fetch(`${BASE}/api/dataset/csv/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "CSV upload failed");
  }
  return res.json();
}

export async function testMysqlConnection(creds: any): Promise<{tables: string[]}> {
  const res = await fetch(`${BASE}/api/dataset/mysql/test-connection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(creds),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Connection test failed");
  }
  return res.json();
}

export async function registerMysqlDataset(req: any): Promise<{dataset_id: string, message: string}> {
  const res = await fetch(`${BASE}/api/dataset/mysql/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "MySQL registration failed");
  }
  return res.json();
}

export async function fetchDatasetSchema(datasetId: string) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/schema`);
  if (!res.ok) throw new Error("Failed to fetch schema");
  return res.json();
}

export async function fetchDatasetPreview(datasetId: string, limit = 50, offset = 0) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/preview?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error("Failed to fetch preview");
  return res.json();
}

export async function fetchDatasetHistory(datasetId: string): Promise<{history: Mutation[]}> {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/history`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function confirmDatasetMutation(datasetId: string, req: any) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: any) => d.msg || String(d)).join(", ")
      : detail || "Mutation execution failed";
    throw new Error(message);
  }
  return res.json();
}

export async function undoDatasetMutation(datasetId: string, mutationId: string) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/undo/${mutationId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Undo failed");
  }
  return res.json();
}

export async function resetDataset(datasetId: string) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/reset`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Reset failed");
  }
  return res.json();
}

export async function syncMysqlSchema(datasetId: string) {
  const res = await fetch(`${BASE}/api/dataset/${datasetId}/sync`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Sync failed");
  }
  return res.json();
}

export function getDownloadUrl(datasetId: string) {
  return `${BASE}/api/dataset/${datasetId}/download`;
}
