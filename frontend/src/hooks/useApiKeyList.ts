import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { ApiKeysService } from "@/client"

export const apiKeyListQueryOptions = queryOptions({
  queryKey: ["api-keys"],
  queryFn: async () => {
    const response = await ApiKeysService.apiKeysListApiKeys({
      query: { skip: 0, limit: 100 },
    })
    return response.data
  },
  staleTime: 60_000,
})

export function useApiKeyList() {
  return useQuery(apiKeyListQueryOptions)
}

export function useApiKeyListSuspense() {
  return useSuspenseQuery(apiKeyListQueryOptions)
}
