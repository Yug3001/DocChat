import { Document } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL;

export async function uploadDocument(
  file: File,
  sessionId: string
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("session_id", sessionId);

  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  const data = await res.json();
  return data.document;
}

export async function uploadMedicalImage(
  file: File,
  sessionId: string
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("session_id", sessionId);

  const res = await fetch(`${BASE}/api/upload/medical`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Medical image upload failed");
  }
  const data = await res.json();
  return data.document;
}


export async function fetchDocuments(sessionId: string): Promise<Document[]> {
  const res = await fetch(`${BASE}/api/documents/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function deleteDocument(
  docId: string,
  sessionId: string
): Promise<void> {
  const res = await fetch(
    `${BASE}/api/documents/${docId}?session_id=${sessionId}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Delete failed");
}

export async function clearSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/session/${sessionId}/clear`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to clear session");
}

export async function ingestWebsite(
  url: string,
  sessionId: string,
  crawlLinks: boolean = true,
  maxPages: number = 5
): Promise<Document> {
  const res = await fetch(`${BASE}/api/website/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      session_id: sessionId,
      crawl_links: crawlLinks,
      max_pages: maxPages,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Website ingestion failed");
  }
  const data = await res.json();
  return data.document;
}