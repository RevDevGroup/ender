import { Calendar, CreditCard } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useQuota } from "@/hooks/useQuota"
import UpgradePlanDialog from "./UpgradePlanDialog"

function ProgressBar({ value, max }: { value: number; max: number }) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const isNearLimit = percentage >= 80
  const isAtLimit = percentage >= 100

  return (
    <div className="w-full bg-secondary rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all ${
          isAtLimit
            ? "bg-destructive"
            : isNearLimit
              ? "bg-yellow-500"
              : "bg-primary"
        }`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

function QuotaCard() {
  const { data: quota, isLoading } = useQuota()

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A"
    return new Date(dateStr).toLocaleDateString()
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <CreditCard className="h-5 w-5 text-[#2dd4a8]" />
          Current Plan
        </CardTitle>
        <CardDescription>Your usage and limits</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold capitalize">
                {quota?.plan || "Free"}
              </span>
              <UpgradePlanDialog currentPlan={quota?.plan} />
            </div>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">SMS Usage</span>
                  <span>
                    {quota?.sms_sent_this_month ?? 0} /{" "}
                    {quota?.max_sms_per_month ?? 0}
                  </span>
                </div>
                <ProgressBar
                  value={quota?.sms_sent_this_month ?? 0}
                  max={quota?.max_sms_per_month ?? 0}
                />
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Devices</span>
                  <span>
                    {quota?.devices_registered ?? 0} / {quota?.max_devices ?? 0}
                  </span>
                </div>
                <ProgressBar
                  value={quota?.devices_registered ?? 0}
                  max={quota?.max_devices ?? 0}
                />
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2">
                <Calendar className="h-4 w-4" />
                <span>Resets on {formatDate(quota?.reset_date ?? null)}</span>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default QuotaCard
