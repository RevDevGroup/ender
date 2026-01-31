import { useQuery } from "@tanstack/react-query"
import { FaGithub, FaGoogle } from "react-icons/fa"

import { type OAuthProviderInfo, OauthService } from "@/client"
import { Button } from "@/components/ui/button"

interface OAuthButtonsProps {
  disabled?: boolean
}

export function OAuthButtons({ disabled }: OAuthButtonsProps) {
  const { data: providers, isLoading } = useQuery({
    queryKey: ["oauth-providers"],
    queryFn: async () => {
      const response = await OauthService.oauthListProviders()
      return response.data
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  })

  const handleOAuthLogin = async (providerName: string) => {
    try {
      const response = await OauthService.oauthAuthorize({
        path: { provider: providerName as "google" | "github" },
      })
      if (response.data?.authorization_url) {
        // Redirect to OAuth provider
        window.location.href = response.data.authorization_url
      }
    } catch (error) {
      console.error("OAuth error:", error)
    }
  }

  const enabledProviders =
    providers?.providers?.filter((p: OAuthProviderInfo) => p.enabled) ?? []

  if (isLoading || enabledProviders.length === 0) {
    return null
  }

  return (
    <div className="grid gap-3">
      {enabledProviders.map((provider: OAuthProviderInfo) => (
        <Button
          key={provider.name}
          variant="outline"
          type="button"
          disabled={disabled}
          onClick={() => handleOAuthLogin(provider.name)}
          className="w-full"
        >
          {provider.name === "google" && <FaGoogle className="mr-2 h-4 w-4" />}
          {provider.name === "github" && <FaGithub className="mr-2 h-4 w-4" />}
          Continue with{" "}
          {provider.name.charAt(0).toUpperCase() + provider.name.slice(1)}
        </Button>
      ))}
    </div>
  )
}
