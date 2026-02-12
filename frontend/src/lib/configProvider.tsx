'use client';

import React, { createContext, useContext } from 'react';
import { useQuery } from '@tanstack/react-query';
import { runtimeConfigApi } from '@/services/api';

interface RuntimeConfig {
  [key: string]: any;
}

const ConfigContext = createContext<RuntimeConfig>({});

export function useRuntimeConfig(): RuntimeConfig {
  return useContext(ConfigContext);
}

export function useConfigValue<T>(key: string, defaultValue: T): T {
  const config = useRuntimeConfig();
  const value = config[key];
  if (value === undefined || value === null) return defaultValue;
  // Parse numeric strings
  if (typeof defaultValue === 'number' && typeof value === 'string') {
    const parsed = Number(value);
    return (isNaN(parsed) ? defaultValue : parsed) as T;
  }
  return value as T;
}

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const { data: config } = useQuery({
    queryKey: ['runtime-config'],
    queryFn: runtimeConfigApi.getRuntimeConfig,
    staleTime: 5 * 60 * 1000, // 5-min cache
    retry: 2,
    refetchOnWindowFocus: false,
  });

  return (
    <ConfigContext.Provider value={config || {}}>
      {children}
    </ConfigContext.Provider>
  );
}
