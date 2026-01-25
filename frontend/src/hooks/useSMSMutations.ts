import { useMutation, useQueryClient } from "@tanstack/react-query"

import { type SMSMessageCreate, SmsService } from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useSendSMS() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: SMSMessageCreate) =>
      SmsService.sendSms({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("SMS sent successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["SMS"] })
    },
  })
}
