import { useCallback, useEffect, useState } from "react";
import { api, AuthError } from "./api";

type State<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  unauthorized: boolean;
  reload: () => void;
};

/** Fetch an admin endpoint and refetch whenever its path or params change. */
export function useApi<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): State<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [unauthorized, setUnauthorized] = useState(false);
  const [tick, setTick] = useState(0);

  const key = JSON.stringify([path, params, tick]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api<T>(path, params)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
        setUnauthorized(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setUnauthorized(err instanceof AuthError);
        setError(err.message);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setTick((n) => n + 1), []);

  return { data, error, loading, unauthorized, reload };
}
