import { useQuery } from "@tanstack/react-query"
import { SmsService } from "@/client"

export function useDeviceList() {
  return useQuery({
    queryKey: ["devices"],
    queryFn: () => SmsService.listDevices(),
    staleTime: 60_000,
  })
}
