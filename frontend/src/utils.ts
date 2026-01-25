import { AxiosError } from "axios"
import type { ApiError } from "./client"

function extractErrorMessage(err: ApiError): string {
  if (err instanceof AxiosError) {
    return err.message
  }

  const errDetail = (err.body as any)?.detail

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

  return "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: ApiError,
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
