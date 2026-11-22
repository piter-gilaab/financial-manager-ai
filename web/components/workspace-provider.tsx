"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import type { ApiHealth, DatasetSummary } from "@/lib/types";

interface WorkspaceContextValue {
  datasets: DatasetSummary[];
  loadingDatasets: boolean;
  datasetError: string | null;
  selectedDataset: DatasetSummary | null;
  health: ApiHealth;
  selectDataset: (dataset: DatasetSummary | null) => void;
  refreshDatasets: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<DatasetSummary | null>(null);
  const [health, setHealth] = useState<ApiHealth>("checking");

  const refreshDatasets = useCallback(async () => {
    setLoadingDatasets(true);
    try {
      const response = await api.datasets();
      setDatasets(response.data);
      setDatasetError(null);
      setHealth("healthy");
      setSelectedDataset((current) => current
        ? response.data.find((item) => item.dataset_id === current.dataset_id) || current
        : null);
    } catch (error) {
      setDatasetError(error instanceof Error ? error.message : "Datasets could not be loaded.");
      setHealth("unavailable");
    } finally {
      setLoadingDatasets(false);
    }
  }, []);

  useEffect(() => {
    void Promise.all([
      refreshDatasets(),
      api.health().then(() => setHealth("healthy")).catch(() => setHealth("unavailable")),
    ]);
  }, [refreshDatasets]);

  const value = useMemo(() => ({
    datasets, loadingDatasets, datasetError, selectedDataset, health, selectDataset: setSelectedDataset, refreshDatasets,
  }), [datasets, loadingDatasets, datasetError, selectedDataset, health, refreshDatasets]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return context;
}
