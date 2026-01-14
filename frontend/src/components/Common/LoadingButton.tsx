import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"

interface LoadingButtonProps {
  children: React.ReactNode
  loading?: boolean
  [key: string]: any
}

export const LoadingButton = ({
  children,
  loading = false,
  ...mergeProps
}: LoadingButtonProps) => {
  return (
    <Button disabled={loading} {...mergeProps}>
      {loading ? <Spinner /> : null}
      {children}
    </Button>
  )
}
