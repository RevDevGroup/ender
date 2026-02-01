import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, ExternalLink } from "lucide-react"
import { useState } from "react"

import { PlansService, type UserPlanPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
import { LoadingButton } from "@/components/ui/loading-button"
import { Skeleton } from "@/components/ui/skeleton"
import useCustomToast from "@/hooks/useCustomToast"
import { usePlanList } from "@/hooks/usePlanList"

interface UpgradePlanDialogProps {
  currentPlan?: string
}

// Response type from the upgrade API
interface UpgradeResponse {
  status: "activated" | "pending_payment" | "pending_authorization"
  plan: string
  message: string
  payment_url?: string
  authorization_url?: string
}

function PlanCard({
  plan,
  isCurrentPlan,
  isSelected,
  onSelect,
}: {
  plan: UserPlanPublic
  isCurrentPlan: boolean
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <Card
      className={`relative cursor-pointer transition-colors hover:bg-accent/50 ${
        isSelected ? "border-primary ring-1 ring-primary" : ""
      } ${isCurrentPlan ? "bg-accent/30" : ""}`}
      onClick={onSelect}
    >
      {isCurrentPlan && (
        <div className="absolute -top-3 left-4 bg-primary text-primary-foreground text-xs px-2 py-1 rounded">
          Current Plan
        </div>
      )}
      <CardHeader className="pb-2">
        <CardTitle className="capitalize">{plan.name}</CardTitle>
        <CardDescription>
          <span className="text-2xl font-bold text-foreground">
            ${plan.price?.toFixed(2) ?? "0.00"}
          </span>
          <span className="text-muted-foreground">/month</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2">
            <Check className="h-4 w-4 text-primary" />
            {plan.max_sms_per_month?.toLocaleString() ?? 0} SMS per month
          </li>
          <li className="flex items-center gap-2">
            <Check className="h-4 w-4 text-primary" />
            {plan.max_devices ?? 0} device
            {(plan.max_devices ?? 0) !== 1 ? "s" : ""}
          </li>
        </ul>
      </CardContent>
    </Card>
  )
}

function UpgradePlanDialog({ currentPlan }: UpgradePlanDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [pendingPayment, setPendingPayment] = useState<{
    url: string
    plan: string
  } | null>(null)
  const { data: plansData, isLoading } = usePlanList()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast, showInfoToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (planId: string) =>
      PlansService.plansUpgradePlan({
        body: { plan_id: planId, payment_method: "invoice" },
      }),
    onSuccess: (response) => {
      const data = response.data as UpgradeResponse

      if (data.status === "activated") {
        // Free plan - activated immediately
        queryClient.invalidateQueries({ queryKey: ["quota"] })
        showSuccessToast("Plan activated successfully")
        setIsOpen(false)
        setSelectedPlanId(null)
      } else if (data.status === "pending_payment" && data.payment_url) {
        // Paid plan - show payment link
        setPendingPayment({ url: data.payment_url, plan: data.plan })
        showInfoToast("Please complete payment to activate your plan")
      } else if (
        data.status === "pending_authorization" &&
        data.authorization_url
      ) {
        // Authorization flow - redirect to provider
        window.location.href = data.authorization_url
      }
    },
    onError: () => {
      showErrorToast("Failed to upgrade plan. Please try again.")
    },
  })

  const handleSubmit = () => {
    if (selectedPlanId) {
      mutation.mutate(selectedPlanId)
    }
  }

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (!open) {
      setSelectedPlanId(null)
      setPendingPayment(null)
    }
  }

  const handlePaymentRedirect = () => {
    if (pendingPayment?.url) {
      window.open(pendingPayment.url, "_blank")
    }
  }

  const selectedPlan = plansData?.data?.find((p) => p.id === selectedPlanId)
  const isCurrentPlanSelected =
    selectedPlan?.name.toLowerCase() === currentPlan?.toLowerCase()

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm">Upgrade Plan</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {pendingPayment ? "Complete Payment" : "Upgrade Your Plan"}
          </DialogTitle>
          <DialogDescription>
            {pendingPayment
              ? `Complete payment to activate ${pendingPayment.plan} plan`
              : "Choose the plan that best fits your needs"}
          </DialogDescription>
        </DialogHeader>

        {pendingPayment ? (
          // Payment pending view
          <div className="py-8 text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
              <ExternalLink className="h-8 w-8 text-primary" />
            </div>
            <p className="text-muted-foreground">
              Click the button below to complete your payment on QvaPay. Once
              payment is confirmed, your plan will be activated automatically.
            </p>
            <Button onClick={handlePaymentRedirect} size="lg" className="gap-2">
              <ExternalLink className="h-4 w-4" />
              Pay with QvaPay
            </Button>
            <p className="text-xs text-muted-foreground">
              You will be redirected to QvaPay to complete the payment securely.
            </p>
          </div>
        ) : isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 py-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 py-4">
            {plansData?.data?.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                isCurrentPlan={
                  plan.name.toLowerCase() === currentPlan?.toLowerCase()
                }
                isSelected={selectedPlanId === plan.id}
                onSelect={() => setSelectedPlanId(plan.id)}
              />
            ))}
          </div>
        )}

        <DialogFooter>
          {pendingPayment ? (
            <Button variant="outline" onClick={() => setPendingPayment(null)}>
              Choose Different Plan
            </Button>
          ) : (
            <>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton
                onClick={handleSubmit}
                loading={mutation.isPending}
                disabled={!selectedPlanId || isCurrentPlanSelected}
              >
                {isCurrentPlanSelected ? "Current Plan" : "Confirm Upgrade"}
              </LoadingButton>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default UpgradePlanDialog
