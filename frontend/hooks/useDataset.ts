import { useState, useCallback, useEffect } from "react";
import { fetchDatasetSchema, fetchDatasetPreview, fetchDatasetHistory, confirmDatasetMutation, undoDatasetMutation, resetDataset, syncMysqlSchema } from "@/lib/datasetApi";
import { Mutation } from "@/lib/types";

export function useDataset(datasetId: string | null) {
  const [schema, setSchema] = useState<any>(null);
  const [datasetMeta, setDatasetMeta] = useState<any>(null);
  const [rowCount, setRowCount] = useState<number>(0);
  const [sampleRows, setSampleRows] = useState<any[]>([]);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [history, setHistory] = useState<Mutation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSchema = useCallback(async () => {
    if (!datasetId) return;
    try {
      const data = await fetchDatasetSchema(datasetId);
      setSchema(data.schema);
      setDatasetMeta(data.dataset);
      setRowCount(data.row_count);
      setSampleRows(data.sample_rows);
    } catch (e: any) {
      setError(e.message);
    }
  }, [datasetId]);

  const loadPreview = useCallback(async (limit = 50, offset = 0) => {
    if (!datasetId) return;
    setLoading(true);
    try {
      const data = await fetchDatasetPreview(datasetId, limit, offset);
      setPreviewData(data.data);
      setRowCount(data.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  const loadHistory = useCallback(async () => {
    if (!datasetId) return;
    try {
      const data = await fetchDatasetHistory(datasetId);
      setHistory(data.history);
    } catch (e: any) {
      setError(e.message);
    }
  }, [datasetId]);

  const confirmMutation = useCallback(async (req: any) => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await confirmDatasetMutation(datasetId, req);
      await Promise.all([loadSchema(), loadPreview(), loadHistory()]);
      return result;
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [datasetId, loadSchema, loadPreview, loadHistory]);

  const undoMutation = useCallback(async (mutationId: string) => {
    if (!datasetId) return;
    setLoading(true);
    try {
      await undoDatasetMutation(datasetId, mutationId);
      await Promise.all([loadSchema(), loadPreview(), loadHistory()]);
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [datasetId, loadSchema, loadPreview, loadHistory]);

  const reset = useCallback(async () => {
    if (!datasetId) return;
    setLoading(true);
    try {
      await resetDataset(datasetId);
      await Promise.all([loadSchema(), loadPreview(), loadHistory()]);
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [datasetId, loadSchema, loadPreview, loadHistory]);

  const syncSchema = useCallback(async () => {
    if (!datasetId || datasetMeta?.source_type !== "MYSQL") return;
    setLoading(true);
    try {
      const result = await syncMysqlSchema(datasetId);
      await loadSchema();
      return result;
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [datasetId, datasetMeta?.source_type, loadSchema]);

  useEffect(() => {
    if (datasetId) {
      loadSchema();
      loadPreview();
      loadHistory();
    } else {
      setSchema(null);
      setDatasetMeta(null);
      setRowCount(0);
      setSampleRows([]);
      setPreviewData([]);
      setHistory([]);
    }
  }, [datasetId, loadSchema, loadPreview, loadHistory]);

  return {
    datasetMeta,
    schema,
    rowCount,
    sampleRows,
    previewData,
    history,
    loading,
    error,
    loadSchema,
    loadPreview,
    loadHistory,
    confirmMutation,
    undoMutation,
    reset,
    syncSchema
  };
}
