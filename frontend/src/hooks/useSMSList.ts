import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export type SMSMessageType = "all" | "incoming" | "outgoing"

export const smsListQueryOptions = (messageType: SMSMessageType = "all") =>
  queryOptions({
    queryKey: ["sms", messageType],
    queryFn: () =>
      SmsService.listMessages({
        skip: 0,
        limit: 100,
        messageType: messageType === "all" ? undefined : messageType,
      }),
    staleTime: 60_000,
  })

export function useSMSList(messageType: SMSMessageType = "all") {
  return useQuery(smsListQueryOptions(messageType))
}

export function useSMSListSuspense(messageType: SMSMessageType = "all") {
  return useSuspenseQuery(smsListQueryOptions(messageType))
}
