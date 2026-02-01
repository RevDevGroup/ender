import { toast } from "sonner"

const useCustomToast = () => {
  const showSuccessToast = (description: string) => {
    toast.success("Success!", {
      description,
    })
  }

  const showErrorToast = (description: string) => {
    toast.error("Something went wrong!", {
      description,
    })
  }

  const showInfoToast = (description: string) => {
    toast.info("Info", {
      description,
    })
  }

  return { showSuccessToast, showErrorToast, showInfoToast }
}

export default useCustomToast
