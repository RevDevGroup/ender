import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { Mail } from "lucide-react"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/check-email")({
  component: CheckEmail,
  validateSearch: (search: Record<string, unknown>) => ({
    email: (search.email as string) || "",
  }),
  head: () => ({
    meta: [
      {
        title: "Check Your Email",
      },
    ],
  }),
})

function CheckEmail() {
  const { email } = Route.useSearch()

  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="rounded-full bg-primary/10 p-4">
          <Mail className="h-12 w-12 text-primary" />
        </div>

        <h1 className="text-2xl">Check your email</h1>

        <p className="text-muted-foreground">
          We've sent a verification link to{" "}
          {email ? (
            <span className="font-medium text-foreground">{email}</span>
          ) : (
            "your email address"
          )}
          . Click the link in the email to verify your account.
        </p>

        <div className="text-sm text-muted-foreground">
          <p>Didn't receive the email?</p>
          <p>Check your spam folder or try signing up again.</p>
        </div>

        <div className="flex gap-4 mt-4">
          <Button variant="outline" asChild>
            <RouterLink to="/login">Go to Login</RouterLink>
          </Button>
          <Button variant="outline" asChild>
            <RouterLink to="/signup">Sign Up Again</RouterLink>
          </Button>
        </div>
      </div>
    </AuthLayout>
  )
}

export default CheckEmail
