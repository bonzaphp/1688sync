import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';
import { ApiResponse, PaginationParams } from '../types';

interface UseApiOptions<T> {
  immediate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  execute: () => Promise<T | null>;
  reset: () => void;
}

export function useApi<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  options: UseApiOptions<T> = {}
): UseApiResult<T> {
  const { immediate = false, onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async (): Promise<T | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiCall();

      if (response.success && response.data) {
        setData(response.data);
        onSuccess?.(response.data);
        return response.data;
      } else {
        throw new Error(response.error || '请求失败');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('未知错误');
      setError(error);
      onError?.(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiCall, onSuccess, onError]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [immediate, execute]);

  return {
    data,
    loading,
    error,
    execute,
    reset
  };
}

interface UsePaginatedApiOptions<T> extends UseApiOptions<T[]> {
  initialParams?: PaginationParams;
}

interface UsePaginatedApiResult<T> extends UseApiResult<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  } | null;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  setParams: (params: PaginationParams) => void;
  refresh: () => Promise<T[] | null>;
}

export function usePaginatedApi<T>(
  apiCall: (params: PaginationParams) => Promise<ApiResponse<T[]>>,
  options: UsePaginatedApiOptions<T> = {}
): UsePaginatedApiResult<T> {
  const { initialParams = { page: 1, limit: 20 }, ...apiOptions } = options;

  const [params, setParams] = useState<PaginationParams>(initialParams);
  const [pagination, setPagination] = useState<UsePaginatedApiResult<T>['pagination']>(null);

  const apiCallWithParams = useCallback(() => apiCall(params), [apiCall, params]);

  const {
    data,
    loading,
    error,
    execute,
    reset
  } = useApi(apiCallWithParams, {
    ...apiOptions,
    onSuccess: (responseData) => {
      // 从响应中提取分页信息（假设API返回包含pagination字段）
      // 这里需要根据实际API响应结构调整
      setPagination({
        page: params.page || 1,
        limit: params.limit || 20,
        total: 0, // 需要从API响应中获取
        totalPages: 0, // 需要从API响应中获取
      });
      apiOptions.onSuccess?.(responseData);
    }
  });

  const setPage = useCallback((page: number) => {
    setParams(prev => ({ ...prev, page }));
  }, []);

  const setLimit = useCallback((limit: number) => {
    setParams(prev => ({ ...prev, limit, page: 1 }));
  }, []);

  const updateParams = useCallback((newParams: PaginationParams) => {
    setParams(prev => ({ ...prev, ...newParams }));
  }, []);

  const refresh = useCallback(async () => {
    return await execute();
  }, [execute]);

  return {
    data,
    loading,
    error,
    execute,
    reset,
    pagination,
    setPage,
    setLimit,
    setParams: updateParams,
    refresh
  };
}

// 防抖Hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 防抖API调用Hook
export function useDebouncedApi<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  delay: number = 300,
  options: UseApiOptions<T> = {}
): UseApiResult<T> & { trigger: () => void } {
  const [trigger, setTrigger] = useState<number>(0);
  const debouncedTrigger = useDebounce(trigger, delay);

  const apiCallWithTrigger = useCallback(() => {
    // 每次trigger变化时返回一个新的Promise来触发API调用
    return apiCall();
  }, [apiCall]);

  const result = useApi(apiCallWithTrigger, {
    ...options,
    immediate: false
  });

  useEffect(() => {
    if (debouncedTrigger > 0) {
      result.execute();
    }
  }, [debouncedTrigger]);

  const manualTrigger = useCallback(() => {
    setTrigger(prev => prev + 1);
  }, []);

  return {
    ...result,
    trigger: manualTrigger
  };
}