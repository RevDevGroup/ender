import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  type SMSDeviceCreate,
  type SMSDeviceUpdate,
  SmsService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateDevice() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: SMSDeviceCreate) =>
      SmsService.createDevice({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Device created successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] })
    },
  })
}

export function useUpdateDevice(deviceId: string) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: SMSDeviceUpdate) =>
      SmsService.updateDevice({ deviceId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Device updated successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] })
    },
  })
}

export function useDeleteDevice() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (deviceId: string) => SmsService.deleteDevice({ deviceId }),
    onSuccess: () => {
      showSuccessToast("The device was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] })
    },
  })
}
