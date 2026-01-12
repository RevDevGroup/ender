import { useQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"
export function useSMSDetails(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["sms", id],
    queryFn: () => SmsService.getMessage({ messageId: id }),
    enabled,
    staleTime: 60_000,
  })
}
