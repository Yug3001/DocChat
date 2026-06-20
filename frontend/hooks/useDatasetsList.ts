import { useState, useCallback, useEffect } from "react";
import { fetchDatasetsList } from "@/lib/datasetApi";
import { Dataset } from "@/lib/types";

export function useDatasetsList() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDatasetsList();
      setDatasets(data.datasets);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  return {
    datasets,
    loading,
    error,
    loadDatasets,
  };
}
