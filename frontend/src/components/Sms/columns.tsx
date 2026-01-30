import type { ColumnDef } from "@tanstack/react-table"
import { Check, Copy } from "lucide-react"
import type { SmsMessagePublic } from "@/client"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { Button } from "../ui/button"
import { SMSActionsMenu } from "./SMSActionsMenu"

function CopyId({ id }: { id: string }) {
  const [copiedText, copy] = useCopyToClipboard()
  const isCopied = copiedText === id

  return (
    <div className="flex items-center gap-1.5 group">
      <span className="font-mono text-xs text-muted-foreground">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copy(id)}
      >
        {isCopied ? (
          <Check className="size-3 text-green-500" />
        ) : (
          <Copy className="size-3" />
        )}
        <span className="sr-only">Copy ID</span>
      </Button>
    </div>
  )
}

export const columns: ColumnDef<SmsMessagePublic>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "device_id",
    header: "Device ID",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.device_id}</span>
    ),
  },
  {
    accessorKey: "to",
    header: "To",
    cell: ({ row }) => <span className="font-medium">{row.original.to}</span>,
  },
  {
    accessorKey: "message_type",
    header: "Message Type",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.message_type}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.status}</span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <SMSActionsMenu sms={row.original} />
      </div>
    ),
  },
]
