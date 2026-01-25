import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Ban } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { ApiKeysService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface RevokeApiKeyProps {
  id: string
  onSuccess: () => void
}

const RevokeApiKey = ({ id, onSuccess }: RevokeApiKeyProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const revokeApiKey = async (apiKeyId: string) => {
    await ApiKeysService.revokeApiKey({ apiKeyId })
  }

  const mutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      showSuccessToast("API key revoked successfully")
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
    },
  })

  const onSubmit = async () => {
    mutation.mutate(id)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Ban />
        Revoke
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Revoke API Key</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke this API key? It will no longer be
              able to authenticate API requests.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
            >
              Revoke
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default RevokeApiKey
