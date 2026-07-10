import { useState, useEffect } from 'react';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useApi<T>(url: string, intervalMs?: number): ApiState<T> {
  const [data, setData]       = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [tick, setTick]       = useState(0);

  const refresh = () => setTick(t => t + 1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(url)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(d => { if (!cancelled) { setData(d); setError(null); } })
      .catch(e => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [url, tick]);

  useEffect(() => {
    if (!intervalMs) return;
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return { data, loading, error, refresh };
}
