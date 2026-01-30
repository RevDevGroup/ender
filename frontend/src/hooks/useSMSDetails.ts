import { useQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export function useSMSDetails(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["sms", id],
    queryFn: async () => {
      const response = await SmsService.smsGetMessage({
        path: { message_id: id },
      })
      return response.data
    },
    enabled,
    staleTime: 60_000,
  })
}
