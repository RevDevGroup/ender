import { queryOptions, useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { WebhooksService } from "@/client"

export const webhookListQueryOptions = queryOptions({
  queryKey: ["webhooks"],
  queryFn: async () => {
    const response = await WebhooksService.webhooksListWebhooks({
      query: { skip: 0, limit: 100 },
    })
    return response.data
  },
  staleTime: 60_000,
})

export function useWebhookList() {
  return useQuery(webhookListQueryOptions)
}

export function useWebhookListSuspense() {
  return useSuspenseQuery(webhookListQueryOptions)
}
