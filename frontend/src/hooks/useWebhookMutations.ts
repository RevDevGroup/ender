import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  type WebhookConfigCreate,
  type WebhookConfigUpdate,
  WebhooksService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateWebhook() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: WebhookConfigCreate) =>
      WebhooksService.createWebhook({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Webhook created successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })
}

export function useUpdateWebhook(webhookId: string) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: WebhookConfigUpdate) =>
      WebhooksService.updateWebhook({ webhookId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Webhook updated successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (webhookId: string) =>
      WebhooksService.deleteWebhook({ webhookId }),
    onSuccess: () => {
      showSuccessToast("The webhook was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })
}
