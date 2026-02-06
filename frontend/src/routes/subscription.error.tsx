import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { XCircle } from "lucide-react"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/subscription/error")({
  component: SubscriptionError,
  head: () => ({
    meta: [
      {
        title: "Subscription Error",
      },
    ],
  }),
})

function SubscriptionError() {
  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="rounded-full bg-destructive/10 p-4">
          <XCircle className="h-12 w-12 text-destructive" />
        </div>

        <h1 className="text-2xl">Subscription Failed</h1>

        <p className="text-muted-foreground">
          We couldn't complete your subscription. This could be because the
          payment was cancelled or there was an issue with the authorization.
        </p>

        <div className="text-sm text-muted-foreground">
          <p>Don't worry, no charges have been made.</p>
          <p>You can try again or contact support if the problem persists.</p>
        </div>

        <div className="flex gap-4 mt-4">
          <Button asChild>
            <RouterLink to="/settings">Try Again</RouterLink>
          </Button>
          <Button variant="outline" asChild>
            <RouterLink to="/">Go to Dashboard</RouterLink>
          </Button>
        </div>
      </div>
    </AuthLayout>
  )
}

export default SubscriptionError
