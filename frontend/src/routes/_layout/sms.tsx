import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { SmsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import PendingItems from "@/components/Pending/PendingItems"
import { columns } from "@/components/Sms/columns"
import SendSMS from "@/components/Sms/SendSMS"

function getSmsQueryOptions() {
  return {
    queryFn: () => SmsService.listMessages({ skip: 0, limit: 100 }),
    queryKey: ["sms"],
  }
}

export const Route = createFileRoute("/_layout/sms")({
  component: Sms,
  head: () => ({
    meta: [
      {
        title: "Message Logs - Ender Labs",
      },
    ],
  }),
})

function SMSTableContent() {
  const { data: sms } = useSuspenseQuery(getSmsQueryOptions())

  if (sms.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any sms yet</h3>
        <p className="text-muted-foreground">Send a new sms to get started</p>
      </div>
    )
  }

  return <DataTable columns={columns} data={sms.data} />
}

function SmsTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <SMSTableContent />
    </Suspense>
  )
}

function Sms() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">SMS</h1>
          <p className="text-muted-foreground">Create and manage your SMS</p>
        </div>
        <SendSMS />
      </div>
      <SmsTable />
    </div>
  )
}
