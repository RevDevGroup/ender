import type { ColumnDef } from "@tanstack/react-table"

import type { WebhookConfigPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { WebhookActionsMenu } from "./WebhookActionsMenu"

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

export const columns: ColumnDef<WebhookConfigPublic>[] = [
  {
    accessorKey: "url",
    header: "URL",
    cell: ({ row }) => (
      <span className="font-medium font-mono text-sm truncate max-w-xs block">
        {row.original.url}
      </span>
    ),
  },
  {
    accessorKey: "events",
    header: "Events",
    cell: ({ row }) => {
      const events = row.original.events || "all"
      return <Badge variant="secondary">{events}</Badge>
    },
  },
  {
    accessorKey: "active",
    header: "Status",
    cell: ({ row }) => {
      const isActive = row.original.active
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              isActive ? "bg-green-500" : "bg-gray-400",
            )}
          />
          <span className={isActive ? "" : "text-muted-foreground"}>
            {isActive ? "Active" : "Inactive"}
          </span>
        </div>
      )
    },
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
        <WebhookActionsMenu webhook={row.original} />
      </div>
    ),
  },
]
