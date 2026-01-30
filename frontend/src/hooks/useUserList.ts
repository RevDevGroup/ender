import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { UsersService } from "@/client"

export const userListQueryOptions = queryOptions({
  queryKey: ["users"],
  queryFn: async () => {
    const response = await UsersService.usersReadUsers({
      query: { skip: 0, limit: 100 },
    })
    return response.data
  },
  staleTime: 60_000,
})

export function useUserList() {
  return useQuery(userListQueryOptions)
}

export function useUserListSuspense() {
  return useSuspenseQuery(userListQueryOptions)
}
