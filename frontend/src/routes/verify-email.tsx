import { useMutation } from "@tanstack/react-query"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { CheckCircle, Loader2, XCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { UsersService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/verify-email")({
  component: VerifyEmail,
  validateSearch: (search: Record<string, unknown>) => ({
    token: (search.token as string) || "",
  }),
  head: () => ({
    meta: [
      {
        title: "Verify Email",
      },
    ],
  }),
})

function VerifyEmail() {
  const { token } = Route.useSearch()
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  )
  const [errorMessage, setErrorMessage] = useState("")

  const verifyMutation = useMutation({
    mutationFn: async (token: string) => {
      const response = await UsersService.usersVerifyEmail({
        query: { token },
      })
      return response.data
    },
    onSuccess: () => {
      setStatus("success")
    },
    onError: (error: any) => {
      setStatus("error")
      setErrorMessage(
        error?.response?.data?.detail ||
          "Failed to verify email. The link may be invalid or expired.",
      )
    },
  })

  useEffect(() => {
    if (token) {
      verifyMutation.mutate(token)
    } else {
      setStatus("error")
      setErrorMessage("No verification token provided")
    }
  }, [token, verifyMutation.mutate])

  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6 text-center">
        {status === "loading" && (
          <>
            <Loader2 className="h-16 w-16 animate-spin text-primary" />
            <h1 className="text-2xl font-bold">Verifying your email...</h1>
            <p className="text-muted-foreground">
              Please wait while we verify your email address.
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle className="h-16 w-16 text-green-500" />
            <h1 className="text-2xl font-bold">Email Verified!</h1>
            <p className="text-muted-foreground">
              Your email has been successfully verified. You can now log in to
              your account.
            </p>
            <Button asChild className="mt-4">
              <RouterLink to="/login">Go to Login</RouterLink>
            </Button>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle className="h-16 w-16 text-destructive" />
            <h1 className="text-2xl font-bold">Verification Failed</h1>
            <p className="text-muted-foreground">{errorMessage}</p>
            <div className="flex gap-4 mt-4">
              <Button variant="outline" asChild>
                <RouterLink to="/login">Go to Login</RouterLink>
              </Button>
              <Button asChild>
                <RouterLink to="/signup">Sign Up Again</RouterLink>
              </Button>
            </div>
          </>
        )}
      </div>
    </AuthLayout>
  )
}

export default VerifyEmail
