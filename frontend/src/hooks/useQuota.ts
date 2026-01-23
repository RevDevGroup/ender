import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { PlansService } from "@/client"

export const quotaQueryOptions = queryOptions({
  queryKey: ["quota"],
  queryFn: () => PlansService.getQuota(),
  staleTime: 60_000,
})

export function useQuota() {
  return useQuery(quotaQueryOptions)
}

export function useQuotaSuspense() {
  return useSuspenseQuery(quotaQueryOptions)
}
