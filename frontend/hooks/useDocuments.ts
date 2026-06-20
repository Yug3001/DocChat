import { useState, useCallback } from "react";
import { Document } from "@/lib/types";
import { fetchDocuments, deleteDocument, uploadDocument, uploadMedicalImage, ingestWebsite } from "@/lib/api";

export function useDocuments(sessionId: string) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocuments(sessionId);
      setDocuments(docs);
    } catch {}
  }, [sessionId]);

  const upload = useCallback(
    async (files: File[]) => {
      setUploading(true);
      setUploadError(null);
      try {
        for (const file of files) {
          const doc = await uploadDocument(file, sessionId);
          setDocuments((prev) => [doc, ...prev]);
        }
      } catch (e: any) {
        setUploadError(e.message);
      } finally {
        setUploading(false);
      }
    },
    [sessionId]
  );

  const uploadMedical = useCallback(
    async (files: File[]) => {
      setUploading(true);
      setUploadError(null);
      try {
        for (const file of files) {
          const doc = await uploadMedicalImage(file, sessionId);
          setDocuments((prev) => [doc, ...prev]);
        }
      } catch (e: any) {
        setUploadError(e.message);
      } finally {
        setUploading(false);
      }
    },
    [sessionId]
  );

  const scrapeUrl = useCallback(
    async (url: string, crawlLinks: boolean = true, maxPages: number = 5) => {
      setScraping(true);
      setScrapeError(null);
      try {
        const doc = await ingestWebsite(url, sessionId, crawlLinks, maxPages);
        setDocuments((prev) => [doc, ...prev]);
        return doc;
      } catch (e: any) {
        setScrapeError(e.message);
        throw e;
      } finally {
        setScraping(false);
      }
    },
    [sessionId]
  );

  const remove = useCallback(
    async (docId: string) => {
      await deleteDocument(docId, sessionId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    },
    [sessionId]
  );

  return { documents, uploading, uploadError, scraping, scrapeError, loadDocuments, upload, uploadMedical, scrapeUrl, remove };
}