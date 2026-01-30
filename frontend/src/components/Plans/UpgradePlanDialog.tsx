import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check } from "lucide-react"
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
  const { data: plansData, isLoading } = usePlanList()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (planId: string) =>
      PlansService.plansUpgradePlan({ body: { plan_id: planId } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quota"] })
      showSuccessToast("Plan updated successfully")
      setIsOpen(false)
      setSelectedPlanId(null)
    },
    onError: () => {
      showErrorToast("Failed to update plan. Please contact support.")
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
          <DialogTitle>Upgrade Your Plan</DialogTitle>
          <DialogDescription>
            Choose the plan that best fits your needs
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default UpgradePlanDialog
