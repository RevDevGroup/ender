import { useMutation, useQueryClient } from "@tanstack/react-query"

import { type SmsMessageCreate, SmsService } from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useSendSMS() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async (data: SmsMessageCreate) => {
      const response = await SmsService.smsSendSms({ body: data })
      return response.data
    },
    onSuccess: () => {
      showSuccessToast("SMS sent successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sms"] })
    },
  })
}
