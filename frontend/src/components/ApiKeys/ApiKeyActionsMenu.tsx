import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { ApiKeyPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteApiKey from "./DeleteApiKey"
import RevokeApiKey from "./RevokeApiKey"

interface ApiKeyActionsMenuProps {
  apiKey: ApiKeyPublic
}

export const ApiKeyActionsMenu = ({ apiKey }: ApiKeyActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {apiKey.is_active && (
          <RevokeApiKey id={apiKey.id} onSuccess={() => setOpen(false)} />
        )}
        <DeleteApiKey id={apiKey.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
