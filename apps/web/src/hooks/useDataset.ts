import { useState, useEffect, useCallback, useRef } from 'react';
import { datasetsApi, type Dataset } from '../lib/api';

const POLL_ACTIVE_STATUSES = ['profiling', 'analyzing'];
const POLL_INTERVAL_MS = 2500;

export function useDataset(id: string | undefined) {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const res = await datasetsApi.get(id);
      if (res.data.data) {
        setDataset(res.data.data);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch().finally(() => setLoading(false));
  }, [id, fetch]);

  // Poll while processing
  useEffect(() => {
    if (!dataset) return;

    const isActive = POLL_ACTIVE_STATUSES.includes(dataset.status);
    if (isActive && !pollRef.current) {
      pollRef.current = setInterval(fetch, POLL_INTERVAL_MS);
    } else if (!isActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [dataset?.status, fetch]);

  return { dataset, loading, error, refetch: fetch };
}

export function useDatasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const res = await datasetsApi.list();
      setDatasets(res.data.data || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { datasets, loading, error, refetch: fetch };
}
