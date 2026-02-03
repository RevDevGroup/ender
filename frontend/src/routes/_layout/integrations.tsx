import { createFileRoute } from "@tanstack/react-router"
import { Key } from "lucide-react"
import { Suspense } from "react"

import AddApiKey from "@/components/ApiKeys/AddApiKey"
import { columns } from "@/components/ApiKeys/columns"
import { DataTable } from "@/components/Common/DataTable"
import PendingApiKeys from "@/components/Pending/PendingApiKeys"
import { useApiKeyListSuspense } from "@/hooks/useApiKeyList"
import useAppConfig from "@/hooks/useAppConfig"

export const Route = createFileRoute("/_layout/integrations")({
  component: Integrations,
})

function ApiKeysTableContent() {
  const { data: apiKeys } = useApiKeyListSuspense()

  if (!apiKeys?.data || apiKeys.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Key className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No API keys</h3>
        <p className="text-muted-foreground">
          Create an API key to access the API programmatically
        </p>
      </div>
    )
  }

  return <DataTable columns={columns} data={apiKeys?.data ?? []} />
}

function ApiKeysTable() {
  return (
    <Suspense fallback={<PendingApiKeys />}>
      <ApiKeysTableContent />
    </Suspense>
  )
}

function Integrations() {
  const { config } = useAppConfig()

  return (
    <div className="flex flex-col gap-6">
      <title>{`Integrations - ${config.appName}`}</title>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">Integrations</h1>
          <p className="text-muted-foreground">
            Manage API keys for programmatic access to the API
          </p>
        </div>
        <AddApiKey />
      </div>
      <ApiKeysTable />
    </div>
  )
}
