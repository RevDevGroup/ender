import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { ArrowLeft, Loader2 } from "lucide-react"

import useAppConfig from "@/hooks/useAppConfig"

export const Route = createFileRoute("/terms")({
  component: Terms,
})

function Terms() {
  const { config, isLoading } = useAppConfig()
  const appName = config.appName
  const supportEmail = config.supportEmail

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <title>{`Terms of Service - ${appName}`}</title>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <RouterLink
          to="/login"
          className="mb-8 inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Login
        </RouterLink>

        <article className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Terms of Service
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Last updated:{" "}
              {new Date().toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          </div>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">1. Acceptance of Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              By accessing and using {appName} ("the Service"), you agree to be
              bound by these Terms of Service. The Service is operated by an
              individual based in Cuba, though the service infrastructure is
              hosted internationally. If you do not agree with any part of these
              terms, you may not use the Service.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">2. Description of Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              {appName} is an SMS gateway platform that allows users to send SMS
              messages using registered devices (Android phones or modems) as
              gateways. The Service provides:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>SMS sending capabilities through registered devices</li>
              <li>API access for programmatic SMS sending</li>
              <li>Webhook integrations for receiving notifications</li>
              <li>Quota management and usage tracking</li>
              <li>Multi-device support</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">3. User Accounts</h2>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">3.1 Registration</h3>
              <p className="text-muted-foreground leading-relaxed">
                To use the Service, you must create an account by providing
                accurate and complete information. You are responsible for
                maintaining the confidentiality of your account credentials.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">3.2 Account Security</h3>
              <p className="text-muted-foreground leading-relaxed">
                You are responsible for all activities that occur under your
                account. You must immediately notify us of any unauthorized use
                of your account or any other security breach.
              </p>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">4. Acceptable Use</h2>
            <p className="text-muted-foreground leading-relaxed">
              You agree NOT to use the Service to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>
                Send spam, unsolicited messages, or bulk commercial messages
              </li>
              <li>Harass, threaten, or abuse others</li>
              <li>Send fraudulent, deceptive, or misleading content</li>
              <li>Violate any applicable laws or regulations</li>
              <li>Infringe on intellectual property rights</li>
              <li>Distribute malware or harmful content</li>
              <li>Attempt to gain unauthorized access to systems or data</li>
              <li>
                Send messages that violate telecommunications regulations in any
                jurisdiction
              </li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">5. API Usage</h2>
            <p className="text-muted-foreground leading-relaxed">
              Access to the API is subject to rate limits and quotas based on
              your subscription plan. You agree to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Keep your API keys confidential and secure</li>
              <li>Not share API keys with unauthorized parties</li>
              <li>Respect rate limits and not attempt to circumvent them</li>
              <li>Use the API in accordance with the provided documentation</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              6. Subscription and Payments
            </h2>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">6.1 Plans and Pricing</h3>
              <p className="text-muted-foreground leading-relaxed">
                The Service offers various subscription plans with different
                features and quotas. Pricing is displayed on our platform and
                may be updated periodically with prior notice.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">6.2 Payment Terms</h3>
              <p className="text-muted-foreground leading-relaxed">
                Payments are processed through third-party payment providers. By
                subscribing to a paid plan, you authorize the recurring charges
                according to your billing cycle.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">6.3 Refunds</h3>
              <p className="text-muted-foreground leading-relaxed">
                Due to the nature of the Service, refunds are generally not
                provided for used quotas. Exceptions may be made at our sole
                discretion on a case-by-case basis.
              </p>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">7. Service Availability</h2>
            <p className="text-muted-foreground leading-relaxed">
              We strive to maintain high availability but do not guarantee
              uninterrupted service. The Service may be temporarily unavailable
              due to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Scheduled maintenance (with advance notice when possible)</li>
              <li>Emergency maintenance or security updates</li>
              <li>Factors beyond our control</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              8. Limitation of Liability
            </h2>
            <p className="text-muted-foreground leading-relaxed uppercase text-sm">
              To the maximum extent permitted by law, the Service is provided
              "as is" without warranties of any kind. We are not liable for any
              indirect, incidental, special, consequential, or punitive damages,
              including but not limited to loss of profits, data, or business
              opportunities.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Our total liability for any claims arising from the use of the
              Service shall not exceed the amount you paid for the Service in
              the twelve (12) months preceding the claim.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">9. Indemnification</h2>
            <p className="text-muted-foreground leading-relaxed">
              You agree to indemnify and hold harmless the Service operator from
              any claims, damages, losses, or expenses arising from your use of
              the Service or violation of these Terms.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">10. Termination</h2>
            <p className="text-muted-foreground leading-relaxed">
              We reserve the right to suspend or terminate your account at any
              time for violation of these Terms or for any other reason at our
              discretion. Upon termination:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Your access to the Service will be revoked</li>
              <li>Your data may be deleted after a reasonable period</li>
              <li>Any unused quota will be forfeited</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">11. Changes to Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may modify these Terms at any time. Significant changes will be
              communicated through the Service or via email. Continued use of
              the Service after changes constitutes acceptance of the modified
              Terms.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">12. Governing Law</h2>
            <p className="text-muted-foreground leading-relaxed">
              These Terms shall be governed by and construed in accordance with
              applicable international laws and conventions. Any disputes shall
              be resolved through good-faith negotiation or, if necessary,
              through appropriate legal channels.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">13. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              For questions about these Terms of Service, please contact us at{" "}
              <a
                href={`mailto:${supportEmail}`}
                className="underline hover:text-foreground"
              >
                {supportEmail}
              </a>
              .
            </p>
          </section>

          <div className="mt-8 border-t pt-8">
            <p className="text-sm text-muted-foreground">
              By using {appName}, you acknowledge that you have read,
              understood, and agree to be bound by these Terms of Service.
            </p>
          </div>
        </article>
      </div>
    </div>
  )
}

export default Terms
