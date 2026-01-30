import type { ColumnDef } from "@tanstack/react-table"
import type { SmsMessagePublic } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { SMSActionsMenu } from "./SMSActionsMenu"

interface SMSTableProps {
  data: SmsMessagePublic[]
}

function getStatusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "delivered":
      return "default"
    case "sent":
      return "secondary"
    case "failed":
      return "destructive"
    default:
      return "outline"
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}...`
}

const columns: ColumnDef<SmsMessagePublic>[] = [
  {
    accessorKey: "to",
    header: "To",
    cell: ({ row }) => {
      const msg = row.original
      const display =
        msg.message_type === "incoming" ? msg.from_number || msg.to : msg.to
      return <span className="font-medium">{display}</span>
    },
  },
  {
    accessorKey: "body",
    header: "Body",
    cell: ({ row }) => (
      <span className="max-w-xs truncate" title={row.original.body}>
        {truncateText(row.original.body, 50)}
      </span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={getStatusBadgeVariant(row.original.status || "pending")}>
        {row.original.status || "pending"}
      </Badge>
    ),
  },
  {
    accessorKey: "message_type",
    header: "Type",
    cell: ({ row }) => (
      <Badge variant="outline">{row.original.message_type || "outgoing"}</Badge>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Date",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {formatDate(row.original.created_at)}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => null,
    cell: ({ row }) => <SMSActionsMenu sms={row.original} />,
  },
]

export function SMSTable({ data }: SMSTableProps) {
  // Sort by created_at descending
  const sortedData = [...data].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )

  return <DataTable columns={columns} data={sortedData} />
}
