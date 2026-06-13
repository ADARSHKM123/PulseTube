import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Minimal data-fetching hook: tracks loading/error, ignores stale responses,
 * refetches when `deps` change, and exposes a manual refetch().
 * `silent` refetches update data without flashing the loading state.
 */
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async (silent = false) => {
    const ticket = ++seq.current;
    if (!silent) {
      setLoading(true);
      setError(null);
    }
    try {
      const result = await fetcherRef.current();
      if (ticket === seq.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (ticket === seq.current) setError(err);
    } finally {
      if (ticket === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refetch: load };
}

/** Debounce a fast-changing value (e.g. search input) before it hits the API. */
export function useDebounced(value, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
