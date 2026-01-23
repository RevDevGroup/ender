import type { ColumnDef } from "@tanstack/react-table"

import type { SMSDevicePublic } from "@/client"
import { DeviceActionsMenu } from "@/components/Devices/DeviceActionsMenu"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

function formatDate(dateString: string | null): string {
  if (!dateString) return "Never"
  return new Date(dateString).toLocaleString()
}

function getStatusVariant(
  status: string,
): "default" | "secondary" | "destructive" {
  switch (status.toLowerCase()) {
    case "online":
      return "default"
    case "offline":
      return "secondary"
    default:
      return "secondary"
  }
}

export const columns: ColumnDef<SMSDevicePublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "phone_number",
    header: "Phone Number",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.phone_number}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.original.status
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              status === "online" ? "bg-green-500" : "bg-gray-400",
            )}
          />
          <Badge variant={getStatusVariant(status)}>{status}</Badge>
        </div>
      )
    },
  },
  {
    accessorKey: "last_heartbeat",
    header: "Last Heartbeat",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {formatDate(row.original.last_heartbeat)}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {formatDate(row.original.created_at)}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <DeviceActionsMenu device={row.original} />
      </div>
    ),
  },
]
