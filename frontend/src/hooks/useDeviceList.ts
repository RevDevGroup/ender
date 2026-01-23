import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export const deviceListQueryOptions = queryOptions({
  queryKey: ["devices"],
  queryFn: () => SmsService.listDevices({ skip: 0, limit: 100 }),
  staleTime: 60_000,
})

export function useDeviceList() {
  return useQuery(deviceListQueryOptions)
}

export function useDeviceListSuspense() {
  return useSuspenseQuery(deviceListQueryOptions)
}
