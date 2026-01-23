import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export const smsListQueryOptions = queryOptions({
  queryKey: ["sms"],
  queryFn: () => SmsService.listMessages({ skip: 0, limit: 100 }),
  staleTime: 60_000,
})

export function useSMSList() {
  return useQuery(smsListQueryOptions)
}

export function useSMSListSuspense() {
  return useSuspenseQuery(smsListQueryOptions)
}
