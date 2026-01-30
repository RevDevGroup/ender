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
    mutationFn: async (data: WebhookConfigCreate) => {
      const response = await WebhooksService.webhooksCreateWebhook({
        body: data,
      })
      return response.data
    },
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
    mutationFn: async (data: WebhookConfigUpdate) => {
      const response = await WebhooksService.webhooksUpdateWebhook({
        path: { webhook_id: webhookId },
        body: data,
      })
      return response.data
    },
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
    mutationFn: async (webhookId: string) => {
      const response = await WebhooksService.webhooksDeleteWebhook({
        path: { webhook_id: webhookId },
      })
      return response.data
    },
    onSuccess: () => {
      showSuccessToast("The webhook was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] })
    },
  })
}
