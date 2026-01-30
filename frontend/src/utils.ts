import { AxiosError } from "axios"

function extractErrorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    const errDetail = err.response?.data?.detail

    // Handle array of validation errors
    if (Array.isArray(errDetail) && errDetail.length > 0) {
      return errDetail[0].msg
    }

    // Handle object with message property (e.g., quota errors)
    if (errDetail && typeof errDetail === "object" && errDetail.message) {
      return errDetail.message
    }

    // Handle string detail
    if (typeof errDetail === "string") {
      return errDetail
    }

    return err.message
  }

  return "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: unknown,
) {
  const errorMessage = extractErrorMessage(err)
  this(errorMessage)
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
