import { zodResolver } from "@hookform/resolvers/zod"
import { Cuer } from "cuer"
import { Check, Copy, Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { SmsDeviceCreate } from "@/client"
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
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useAppConfig from "@/hooks/useAppConfig"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { useCreateDevice } from "@/hooks/useDeviceMutations"

const formSchema = z.object({
  name: z
    .string()
    .min(1, { message: "Name is required" })
    .max(255, { message: "Name must be at most 255 characters" }),
  phone_number: z
    .e164()
    .min(1, { message: "Phone number is required" })
    .max(20, { message: "Phone number must be at most 20 characters" }),
})

type FormData = z.infer<typeof formSchema>

const QR_PAYLOAD_VERSION = "0.1"

const AddDevice = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [copiedText, copyToClipboard] = useCopyToClipboard()
  const { config } = useAppConfig()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      phone_number: "",
    },
  })

  const createDeviceMutation = useCreateDevice()

  const onSubmit = (data: SmsDeviceCreate) => {
    createDeviceMutation.mutate(data, {
      onSuccess: (response) => {
        setApiKey(response?.api_key ?? null)
        form.reset()
      },
    })
  }

  const handleClose = (open: boolean) => {
    if (!open) {
      setApiKey(null)
      form.reset()
    }
    setIsOpen(open)
  }

  const getQrPayload = (deviceApiKey: string) => {
    const payload = {
      server_instance: import.meta.env.VITE_API_URL,
      api_key: deviceApiKey,
      version: QR_PAYLOAD_VERSION,
    }
    return JSON.stringify(payload)
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button className="my-4">
          <Plus />
          Add Device
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        {apiKey ? (
          <>
            <DialogHeader>
              <DialogTitle>Device Created</DialogTitle>
              <DialogDescription>
                Your device has been created. Save the API key below - it will
                only be shown once.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-4">
              <div className="flex flex-col items-center gap-3">
                <div className="rounded-lg border bg-white p-4">
                  <Cuer.Root value={getQrPayload(apiKey)} size={200}>
                    <Cuer.Finder fill="black" />
                    <Cuer.Cells fill="black" />
                  </Cuer.Root>
                </div>
                <p className="text-sm text-muted-foreground text-center">
                  Scan this QR code with the {config.appName} Modem app to
                  connect automatically
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Input value={apiKey} readOnly className="font-mono text-sm" />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => copyToClipboard(apiKey)}
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
              <Button onClick={() => handleClose(false)}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Add Device</DialogTitle>
              <DialogDescription>
                Register a new device to send SMS messages.
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
                            placeholder="My Android Phone"
                            type="text"
                            {...field}
                            required
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="phone_number"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Phone Number{" "}
                          <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="+1234567890"
                            type="tel"
                            {...field}
                            required
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <DialogFooter>
                  <DialogClose asChild>
                    <Button
                      variant="outline"
                      disabled={createDeviceMutation.isPending}
                    >
                      Cancel
                    </Button>
                  </DialogClose>
                  <LoadingButton
                    type="submit"
                    loading={createDeviceMutation.isPending}
                  >
                    Create Device
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

export default AddDevice
