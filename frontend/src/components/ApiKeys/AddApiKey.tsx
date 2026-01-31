import { zodResolver } from "@hookform/resolvers/zod"
import { Cuer } from "cuer"
import { Check, Copy, Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { ApiKeyCreate } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { useCreateApiKey } from "@/hooks/useApiKeyMutations"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"

const formSchema = z.object({
  name: z.string().min(1, { message: "Name is required" }),
})

type FormData = z.infer<typeof formSchema>

const QR_PAYLOAD_VERSION = "0.1"

const AddApiKey = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copiedText, copyToClipboard] = useCopyToClipboard()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
    },
  })

  const createApiKeyMutation = useCreateApiKey()

  const onSubmit = (data: ApiKeyCreate) => {
    createApiKeyMutation.mutate(data, {
      onSuccess: (response) => {
        setCreatedKey(response?.key ?? null)
      },
    })
  }

  const handleClose = (open: boolean) => {
    if (!open) {
      form.reset()
      setCreatedKey(null)
      createApiKeyMutation.reset()
    }
    setIsOpen(open)
  }

  const getQrPayload = (apiKey: string) => {
    const payload = {
      server_instance: import.meta.env.VITE_API_URL,
      api_key: apiKey,
      version: QR_PAYLOAD_VERSION,
    }
    return JSON.stringify(payload)
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button className="my-4">
          <Plus />
          Create API Key
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        {createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>API Key Created</DialogTitle>
              <DialogDescription>
                Make sure to copy your API key now. You won't be able to see it
                again.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-4">
              <div className="flex flex-col items-center gap-3">
                <div className="rounded-lg border bg-white p-4">
                  <Cuer.Root value={getQrPayload(createdKey)} size={200}>
                    <Cuer.Finder fill="black" />
                    <Cuer.Cells fill="black" />
                  </Cuer.Root>
                </div>
                <p className="text-sm text-muted-foreground text-center">
                  Scan this QR code with the app to connect automatically
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  value={createdKey}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => copyToClipboard(createdKey)}
                >
                  {copiedText ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button>Done</Button>
              </DialogClose>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Create a new API key for programmatic access to the API.
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)}>
                <div className="grid gap-4 py-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Name <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="My API Key"
                            type="text"
                            {...field}
                            required
                          />
                        </FormControl>
                        <FormDescription>
                          A descriptive name to identify this API key
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <DialogFooter>
                  <DialogClose asChild>
                    <Button
                      variant="outline"
                      disabled={createApiKeyMutation.isPending}
                    >
                      Cancel
                    </Button>
                  </DialogClose>
                  <LoadingButton
                    type="submit"
                    loading={createApiKeyMutation.isPending}
                  >
                    Create
                  </LoadingButton>
                </DialogFooter>
              </form>
            </Form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default AddApiKey
