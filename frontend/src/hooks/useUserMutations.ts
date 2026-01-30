import { useMutation, useQueryClient } from "@tanstack/react-query"

import { type UserCreate, UsersService, type UserUpdate } from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export function useCreateUser() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async (data: UserCreate) => {
      const response = await UsersService.usersCreateUser({ body: data })
      return response.data
    },
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
    mutationFn: async (data: UserUpdate) => {
      const response = await UsersService.usersUpdateUser({
        path: { user_id: userId },
        body: data,
      })
      return response.data
    },
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
    mutationFn: async (userId: string) => {
      const response = await UsersService.usersDeleteUser({
        path: { user_id: userId },
      })
      return response.data
    },
    onSuccess: () => {
      showSuccessToast("The user was deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })
}
