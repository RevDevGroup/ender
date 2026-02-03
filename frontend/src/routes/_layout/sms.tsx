import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { useState } from "react"

import PendingItems from "@/components/Pending/PendingItems"
import SendSMS from "@/components/Sms/SendSMS"
import { SMSTable } from "@/components/Sms/SMSTable"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAppConfig from "@/hooks/useAppConfig"
import { type SMSMessageType, useSMSList } from "@/hooks/useSMSList"

export const Route = createFileRoute("/_layout/sms")({
  component: Sms,
})

function SMSTableContent({ messageType }: { messageType: SMSMessageType }) {
  const { data: sms, isLoading } = useSMSList(messageType)

  if (isLoading) {
    return <PendingItems />
  }

  if (!sms || sms.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No messages found</h3>
        <p className="text-muted-foreground">
          {messageType === "incoming"
            ? "You haven't received any SMS yet"
            : messageType === "outgoing"
              ? "You haven't sent any SMS yet"
              : "You don't have any SMS yet"}
        </p>
      </div>
    )
  }

  return <SMSTable data={sms.data} />
}

function Sms() {
  const [messageType, setMessageType] = useState<SMSMessageType>("all")
  const { config } = useAppConfig()

  return (
    <div className="flex flex-col gap-6">
      <title>{`Message Logs - ${config.appName}`}</title>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">SMS</h1>
          <p className="text-muted-foreground">Create and manage your SMS</p>
        </div>
        <SendSMS />
      </div>

      <Tabs
        value={messageType}
        onValueChange={(value) => setMessageType(value as SMSMessageType)}
      >
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="outgoing">Sent</TabsTrigger>
          <TabsTrigger value="incoming">Received</TabsTrigger>
        </TabsList>
      </Tabs>

      <SMSTableContent messageType={messageType} />
    </div>
  )
}
