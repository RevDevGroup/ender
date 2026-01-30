import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export type SMSMessageType = "all" | "incoming" | "outgoing"

export const smsListQueryOptions = (messageType: SMSMessageType = "all") =>
  queryOptions({
    queryKey: ["sms", messageType],
    queryFn: async () => {
      const response = await SmsService.smsListMessages({
        query: {
          skip: 0,
          limit: 100,
          message_type: messageType === "all" ? undefined : messageType,
        },
      })
      return response.data
    },
    staleTime: 60_000,
  })

export function useSMSList(messageType: SMSMessageType = "all") {
  return useQuery(smsListQueryOptions(messageType))
}

export function useSMSListSuspense(messageType: SMSMessageType = "all") {
  return useSuspenseQuery(smsListQueryOptions(messageType))
}
