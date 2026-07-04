import { useState, useEffect, useCallback } from 'react';

export interface UseApiListResult<T> {
  data: T[] | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T[] | null>>;
}

export default function useApiList<T>(
  fetchFn: () => Promise<T[]>,
  dependencies: any[] = []
): UseApiListResult<T> {
  const [data, setData] = useState<T[] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchFn();
      setData(response);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while fetching data.');
    } finally {
      setIsLoading(false);
    }
  }, [fetchFn]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return {
    data,
    isLoading,
    error,
    refresh: fetchData,
    setData,
  };
}
