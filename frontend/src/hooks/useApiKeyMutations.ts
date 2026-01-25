import { useMutation, useQueryClient } from "@tanstack/react-query"

import { type ApiKeyCreate, ApiKeysService } from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: ApiKeyCreate) =>
      ApiKeysService.createApiKey({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("API key created successfully")
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
    onError: handleError.bind(showErrorToast),
  })
}

export function useDeleteApiKey() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (apiKeyId: string) => ApiKeysService.deleteApiKey({ apiKeyId }),
    onSuccess: () => {
      showSuccessToast("API key deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
  })
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (apiKeyId: string) => ApiKeysService.revokeApiKey({ apiKeyId }),
    onSuccess: () => {
      showSuccessToast("API key revoked successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
  })
}
