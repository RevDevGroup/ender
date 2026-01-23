import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return "Never"
  return new Date(dateString).toLocaleString()
}

export function getStatusVariant(
  status: string,
): "default" | "secondary" | "destructive" {
  switch (status?.toLowerCase()) {
    case "online":
      return "default"
    case "offline":
      return "secondary"
    default:
      return "secondary"
  }
}
