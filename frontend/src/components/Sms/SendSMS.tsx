import { zodResolver } from "@hookform/resolvers/zod"
import { Plus } from "lucide-react"
import { useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { LoadingButton } from "@/components/Common/LoadingButton"
import { MultiSelect } from "@/components/Common/MultiSelect"
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
import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { TagInput } from "@/components/ui/tag-input"
import { useDeviceList } from "@/hooks/useDeviceList"
import { useSendSMS } from "@/hooks/useSMSMutations"

const formSchema = z.object({
  recipients: z
    .array(z.e164().min(1, "Recipient is required"))
    .min(1, "At least one recipient is required"),
  from: z.array(z.string()).min(1, "Device is required"),
  body: z.string().min(1, "Message body is required"),
})

type FormData = z.infer<typeof formSchema>

const SendSMS = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { data: devices } = useDeviceList()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      recipients: [],
      from: [],
      body: "",
    },
  })

  const sendSMSMutation = useSendSMS()

  const onSubmit = (data: FormData) => {
    sendSMSMutation.mutate(
      {
        recipients: data.recipients,
        body: data.body,
        device_id: data.from[0],
      },
      {
        onSuccess: () => {
          form.reset()
          setIsOpen(false)
        },
      },
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="my-4">
          <Plus className="h-4 w-4" />
          Send SMS
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Send SMS</DialogTitle>
          <DialogDescription>
            Fill in the form below to add a sms to be sent.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
          {/* Recipient Field */}
          <Controller
            name="recipients"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={field.name}>
                  To <span className="text-destructive">*</span>
                </FieldLabel>
                <TagInput
                  {...field}
                  id={field.name}
                  placeholder="Phone numbers (space separated)"
                  aria-invalid={fieldState.invalid}
                />
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          {/* Device Selection Field */}
          <Controller
            name="from"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={field.name}>
                  Devices <span className="text-destructive">*</span>
                </FieldLabel>
                <MultiSelect
                  options={(devices?.data || []).map((device) => ({
                    label: device.name || device.id,
                    value: device.id,
                  }))}
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                />
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          {/* Message Body Field */}
          <Controller
            name="body"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={field.name}>
                  SMS Body <span className="text-destructive">*</span>
                </FieldLabel>
                <Input
                  {...field}
                  id={field.name}
                  placeholder="Message Body"
                  aria-invalid={fieldState.invalid}
                />
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          <DialogFooter>
            <DialogClose asChild>
              <Button
                variant="outline"
                type="button"
                disabled={sendSMSMutation.isPending}
              >
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton type="submit" loading={sendSMSMutation.isPending}>
              Save
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default SendSMS
