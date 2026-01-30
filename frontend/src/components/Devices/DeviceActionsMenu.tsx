import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { SmsDevicePublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteDevice from "./DeleteDevice"
import EditDevice from "./EditDevice"

interface DeviceActionsMenuProps {
  device: SmsDevicePublic
}

export const DeviceActionsMenu = ({ device }: DeviceActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditDevice device={device} onSuccess={() => setOpen(false)} />
        <DeleteDevice id={device.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
