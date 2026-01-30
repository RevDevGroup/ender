import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { PlansService } from "@/client"

export const planListQueryOptions = queryOptions({
  queryKey: ["plans"],
  queryFn: async () => {
    const response = await PlansService.plansListPlans()
    return response.data
  },
  staleTime: 300_000, // 5 minutes - plans don't change often
})

export function usePlanList() {
  return useQuery(planListQueryOptions)
}

export function usePlanListSuspense() {
  return useSuspenseQuery(planListQueryOptions)
}
