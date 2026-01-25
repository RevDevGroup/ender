import { useMutation, useQueryClient } from "@tanstack/react-query"

import { type UserCreate, UsersService, type UserUpdate } from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateUser() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: UserCreate) =>
      UsersService.createUser({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User created successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })
}

export function useUpdateUser(userId: string) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (data: UserUpdate) =>
      UsersService.updateUser({ userId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User updated successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (userId: string) => UsersService.deleteUser({ userId }),
    onSuccess: () => {
      showSuccessToast("The user was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })
}
