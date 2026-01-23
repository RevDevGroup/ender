import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { WebhookConfigPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteWebhook from "./DeleteWebhook"
import EditWebhook from "./EditWebhook"

interface WebhookActionsMenuProps {
  webhook: WebhookConfigPublic
}

export const WebhookActionsMenu = ({ webhook }: WebhookActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditWebhook webhook={webhook} onSuccess={() => setOpen(false)} />
        <DeleteWebhook id={webhook.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
