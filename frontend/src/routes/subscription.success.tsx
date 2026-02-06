import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { CheckCircle } from "lucide-react"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/subscription/success")({
  component: SubscriptionSuccess,
  head: () => ({
    meta: [
      {
        title: "Subscription Activated",
      },
    ],
  }),
})

function SubscriptionSuccess() {
  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="rounded-full bg-green-500/10 p-4">
          <CheckCircle className="h-12 w-12 text-green-500" />
        </div>

        <h1 className="text-2xl">Subscription Activated!</h1>

        <p className="text-muted-foreground">
          Your payment has been authorized successfully. Your subscription is
          now active and you can start using all the features of your plan.
        </p>

        <div className="text-sm text-muted-foreground">
          <p>Your first payment will be processed automatically.</p>
          <p>You can manage your subscription in the settings.</p>
        </div>

        <div className="flex gap-4 mt-4">
          <Button asChild>
            <RouterLink to="/">Go to Dashboard</RouterLink>
          </Button>
          <Button variant="outline" asChild>
            <RouterLink to="/settings">View Settings</RouterLink>
          </Button>
        </div>
      </div>
    </AuthLayout>
  )
}

export default SubscriptionSuccess
