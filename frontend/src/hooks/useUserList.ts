import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { UsersService } from "@/client"

export const userListQueryOptions = queryOptions({
  queryKey: ["users"],
  queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
  staleTime: 60_000,
})

export function useUserList() {
  return useQuery(userListQueryOptions)
}

export function useUserListSuspense() {
  return useSuspenseQuery(userListQueryOptions)
}
