import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { SMSMessagePublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import SMSDetails from "./SMSDetails"

interface SMSActionsMenuProps {
  sms: SMSMessagePublic
}

export const SMSActionsMenu = ({ sms }: SMSActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <SMSDetails id={sms.id} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
