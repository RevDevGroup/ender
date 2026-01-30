import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  type SmsDeviceCreate,
  type SmsDeviceUpdate,
  SmsService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateDevice() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async (data: SmsDeviceCreate) => {
      const response = await SmsService.smsCreateDevice({ body: data })
      return response.data
    },
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
    mutationFn: async (data: SmsDeviceUpdate) => {
      const response = await SmsService.smsUpdateDevice({
        path: { device_id: deviceId },
        body: data,
      })
      return response.data
    },
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
    mutationFn: async (deviceId: string) => {
      const response = await SmsService.smsDeleteDevice({
        path: { device_id: deviceId },
      })
      return response.data
    },
    onSuccess: () => {
      showSuccessToast("The device was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] })
    },
  })
}
