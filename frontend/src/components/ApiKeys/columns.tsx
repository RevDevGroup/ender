import type { ColumnDef } from "@tanstack/react-table"

import type { ApiKeyPublic } from "@/client"
import { cn } from "@/lib/utils"
import { ApiKeyActionsMenu } from "./ApiKeyActionsMenu"

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

export const columns: ColumnDef<ApiKeyPublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "key_prefix",
    header: "Key",
    cell: ({ row }) => (
      <span className="font-mono text-sm text-muted-foreground">
        {row.original.key_prefix}
      </span>
    ),
  },
  {
    accessorKey: "is_active",
    header: "Status",
    cell: ({ row }) => {
      const isActive = row.original.is_active
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              isActive ? "bg-green-500" : "bg-gray-400",
            )}
          />
          <span className={isActive ? "" : "text-muted-foreground"}>
            {isActive ? "Active" : "Revoked"}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "last_used_at",
    header: "Last Used",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.last_used_at
          ? formatDate(row.original.last_used_at)
          : "Never"}
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
        <ApiKeyActionsMenu apiKey={row.original} />
      </div>
    ),
  },
]
