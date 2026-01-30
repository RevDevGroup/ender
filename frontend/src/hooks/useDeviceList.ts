import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export const deviceListQueryOptions = queryOptions({
  queryKey: ["devices"],
  queryFn: async () => {
    const response = await SmsService.smsListDevices({
      query: { skip: 0, limit: 100 },
    })
    return response.data
  },
  staleTime: 60_000,
})

export function useDeviceList() {
  return useQuery(deviceListQueryOptions)
}

export function useDeviceListSuspense() {
  return useSuspenseQuery(deviceListQueryOptions)
}
