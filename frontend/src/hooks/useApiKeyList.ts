import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { ApiKeysService } from "@/client"

export const apiKeyListQueryOptions = queryOptions({
  queryKey: ["api-keys"],
  queryFn: () => ApiKeysService.listApiKeys({ skip: 0, limit: 100 }),
  staleTime: 60_000,
})

export function useApiKeyList() {
  return useQuery(apiKeyListQueryOptions)
}

export function useApiKeyListSuspense() {
  return useSuspenseQuery(apiKeyListQueryOptions)
}
