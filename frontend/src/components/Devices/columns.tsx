import type { ColumnDef } from "@tanstack/react-table"

import type { SmsDevicePublic } from "@/client"
import { DeviceActionsMenu } from "@/components/Devices/DeviceActionsMenu"
import { formatDate } from "@/lib/utils"

export const columns: ColumnDef<SmsDevicePublic>[] = [
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
