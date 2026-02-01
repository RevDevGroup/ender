import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Bell,
  CreditCard,
  Loader2,
  MessageSquare,
  Settings2,
} from "lucide-react"

import type { SystemConfigPublic } from "@/client"
import { SystemConfigService } from "@/client"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import useCustomToast from "@/hooks/useCustomToast"

function SystemSettings() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: configs, isLoading } = useQuery({
    queryKey: ["system-config"],
    queryFn: async () => {
      const response = await SystemConfigService.systemConfigListConfigs()
      return response.data
    },
  })

  const updateConfigMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      return SystemConfigService.systemConfigUpdateConfig({
        path: { key },
        body: { value },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-config"] })
      showSuccessToast("Configuration updated successfully")
    },
    onError: () => {
      showErrorToast("Failed to update configuration")
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const getConfigValue = (key: string): string => {
    const config = configs?.data?.find((c: SystemConfigPublic) => c.key === key)
    return config?.value ?? ""
  }

  const handleConfigChange = (key: string, value: string) => {
    updateConfigMutation.mutate({ key, value })
  }

  const handleBooleanChange = (key: string) => (checked: boolean) => {
    updateConfigMutation.mutate({ key, value: checked ? "true" : "false" })
  }

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            General
          </CardTitle>
          <CardDescription>
            Basic application settings and branding
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="app-name">Application Name</Label>
            <Input
              id="app-name"
              defaultValue={getConfigValue("app_name")}
              onBlur={(e) => handleConfigChange("app_name", e.target.value)}
              placeholder="Ender"
              className="w-[300px]"
            />
            <p className="text-sm text-muted-foreground">
              The name displayed throughout the application
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="support-email">Support Email</Label>
            <Input
              id="support-email"
              type="email"
              defaultValue={getConfigValue("support_email")}
              onBlur={(e) =>
                handleConfigChange("support_email", e.target.value)
              }
              placeholder="support@example.com"
              className="w-[300px]"
            />
            <p className="text-sm text-muted-foreground">
              Contact email for user support requests
            </p>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="maintenance-mode">Maintenance Mode</Label>
              <p className="text-sm text-muted-foreground">
                When enabled, users will see a maintenance message
              </p>
            </div>
            <Switch
              id="maintenance-mode"
              checked={getConfigValue("maintenance_mode") === "true"}
              onCheckedChange={handleBooleanChange("maintenance_mode")}
              disabled={updateConfigMutation.isPending}
            />
          </div>
        </CardContent>
      </Card>

      {/* Payment Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Payments
          </CardTitle>
          <CardDescription>
            Configure payment options for subscriptions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="payment-method">Default Payment Method</Label>
            <Select
              value={getConfigValue("default_payment_method")}
              onValueChange={(value) =>
                handleConfigChange("default_payment_method", value)
              }
              disabled={updateConfigMutation.isPending}
            >
              <SelectTrigger id="payment-method" className="w-[300px]">
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="invoice">
                  <div className="flex flex-col items-start">
                    <span>Invoice</span>
                    <span className="text-xs text-muted-foreground">
                      Manual payment via invoice each period
                    </span>
                  </div>
                </SelectItem>
                <SelectItem value="authorized">
                  <div className="flex flex-col items-start">
                    <span>Authorized</span>
                    <span className="text-xs text-muted-foreground">
                      Automatic recurring payments
                    </span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Determines whether new subscriptions use manual invoice payments
              or automatic recurring charges
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="payment-provider">Payment Provider</Label>
            <Select
              value={getConfigValue("payment_provider")}
              onValueChange={(value) =>
                handleConfigChange("payment_provider", value)
              }
              disabled={updateConfigMutation.isPending}
            >
              <SelectTrigger id="payment-provider" className="w-[300px]">
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="qvapay">QvaPay</SelectItem>
                <SelectItem value="tropipay">TropiPay</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Active payment gateway for processing transactions
            </p>
          </div>
        </CardContent>
      </Card>

      {/* SMS Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            SMS
          </CardTitle>
          <CardDescription>
            Configure SMS delivery settings and limits
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="sms-rate-limit">Rate Limit (per minute)</Label>
            <Input
              id="sms-rate-limit"
              type="number"
              defaultValue={getConfigValue("sms_rate_limit_per_minute")}
              onBlur={(e) =>
                handleConfigChange("sms_rate_limit_per_minute", e.target.value)
              }
              className="w-[150px]"
            />
            <p className="text-sm text-muted-foreground">
              Maximum SMS messages a user can send per minute
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="sms-retry">Retry Attempts</Label>
            <Input
              id="sms-retry"
              type="number"
              defaultValue={getConfigValue("sms_retry_attempts")}
              onBlur={(e) =>
                handleConfigChange("sms_retry_attempts", e.target.value)
              }
              className="w-[150px]"
            />
            <p className="text-sm text-muted-foreground">
              Number of retry attempts for failed SMS delivery
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Notifications Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Configure notification and webhook settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="email-notifications">Email Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Send email notifications for important events
              </p>
            </div>
            <Switch
              id="email-notifications"
              checked={getConfigValue("email_notifications_enabled") === "true"}
              onCheckedChange={handleBooleanChange(
                "email_notifications_enabled",
              )}
              disabled={updateConfigMutation.isPending}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="webhook-timeout">Webhook Timeout (seconds)</Label>
            <Input
              id="webhook-timeout"
              type="number"
              defaultValue={getConfigValue("webhook_timeout_seconds")}
              onBlur={(e) =>
                handleConfigChange("webhook_timeout_seconds", e.target.value)
              }
              className="w-[150px]"
            />
            <p className="text-sm text-muted-foreground">
              Timeout for webhook delivery requests
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SystemSettings
