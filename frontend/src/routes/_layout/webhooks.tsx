import { createFileRoute } from "@tanstack/react-router"
import { Webhook } from "lucide-react"
import { Suspense } from "react"

import { DataTable } from "@/components/Common/DataTable"
import PendingWebhooks from "@/components/Pending/PendingWebhooks"
import AddWebhook from "@/components/Webhooks/AddWebhook"
import { columns } from "@/components/Webhooks/columns"
import useAppConfig from "@/hooks/useAppConfig"
import { useWebhookListSuspense } from "@/hooks/useWebhookList"

export const Route = createFileRoute("/_layout/webhooks")({
  component: Webhooks,
})

function WebhooksTableContent() {
  const { data: webhooks } = useWebhookListSuspense()

  if (!webhooks?.data || webhooks.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Webhook className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No webhooks configured</h3>
        <p className="text-muted-foreground">
          Add a webhook to receive notifications when SMS messages arrive
        </p>
      </div>
    )
  }

  return <DataTable columns={columns} data={webhooks?.data ?? []} />
}

function WebhooksTable() {
  return (
    <Suspense fallback={<PendingWebhooks />}>
      <WebhooksTableContent />
    </Suspense>
  )
}

function Webhooks() {
  const { config } = useAppConfig()

  return (
    <div className="flex flex-col gap-6">
      <title>{`Webhooks - ${config.appName}`}</title>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">Webhooks</h1>
          <p className="text-muted-foreground">
            Configure webhooks to receive notifications for incoming SMS
          </p>
        </div>
        <AddWebhook />
      </div>
      <WebhooksTable />
    </div>
  )
}
