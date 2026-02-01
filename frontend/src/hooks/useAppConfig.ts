import { useQuery } from "@tanstack/react-query"

import type { AppSettings } from "@/client"
import { UtilsService } from "@/client"

export interface AppConfig {
  appName: string
  supportEmail: string
}

const DEFAULT_CONFIG: AppConfig = {
  appName: "Ender",
  supportEmail: "support@example.com",
}

export function useAppConfig() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["app-settings"],
    queryFn: async (): Promise<AppSettings> => {
      const response = await UtilsService.utilsGetAppSettings()
      return response.data as AppSettings
    },
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
    retry: 1,
  })

  const config: AppConfig = {
    appName: data?.app_name ?? DEFAULT_CONFIG.appName,
    supportEmail: data?.support_email ?? DEFAULT_CONFIG.supportEmail,
  }

  return {
    config,
    isLoading,
    error,
  }
}

export default useAppConfig
