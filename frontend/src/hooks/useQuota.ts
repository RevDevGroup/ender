import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { PlansService } from "@/client"

export const quotaQueryOptions = queryOptions({
  queryKey: ["quota"],
  queryFn: async () => {
    const response = await PlansService.plansGetQuota()
    return response.data
  },
  staleTime: 60_000,
})

export function useQuota() {
  return useQuery(quotaQueryOptions)
}

export function useQuotaSuspense() {
  return useSuspenseQuery(quotaQueryOptions)
}
