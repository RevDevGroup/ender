import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { ArrowLeft, Loader2 } from "lucide-react"

import useAppConfig from "@/hooks/useAppConfig"

export const Route = createFileRoute("/privacy")({
  component: Privacy,
})

function Privacy() {
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
      <title>{`Privacy Policy - ${appName}`}</title>
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
              Privacy Policy
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
            <h2 className="text-xl font-semibold">1. Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">
              This Privacy Policy describes how {appName} ("we", "us", "the
              Service") collects, uses, and protects your personal information.
              The Service is operated by an individual based in Cuba, with
              infrastructure hosted internationally to ensure reliable service
              delivery.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              We are committed to protecting your privacy and handling your data
              responsibly. By using our Service, you agree to the collection and
              use of information in accordance with this policy.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">2. Information We Collect</h2>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">2.1 Account Information</h3>
              <p className="text-muted-foreground leading-relaxed">
                When you create an account, we collect:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>
                  <strong className="text-foreground">Email address:</strong>{" "}
                  Used for account identification, authentication, and
                  communication
                </li>
                <li>
                  <strong className="text-foreground">Full name:</strong> Used
                  for account personalization
                </li>
                <li>
                  <strong className="text-foreground">Password:</strong> Stored
                  securely using industry-standard hashing algorithms
                </li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">2.2 Service Usage Data</h3>
              <p className="text-muted-foreground leading-relaxed">
                When you use our Service, we automatically collect:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>
                  <strong className="text-foreground">
                    SMS message metadata:
                  </strong>{" "}
                  Recipient numbers, timestamps, delivery status (message
                  content is processed but not permanently stored)
                </li>
                <li>
                  <strong className="text-foreground">
                    Device information:
                  </strong>{" "}
                  Device identifiers, registration tokens for your gateway
                  devices
                </li>
                <li>
                  <strong className="text-foreground">API usage:</strong>{" "}
                  Request logs, API key usage, rate limit data
                </li>
                <li>
                  <strong className="text-foreground">
                    Quota and billing information:
                  </strong>{" "}
                  Usage statistics, subscription details
                </li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">2.3 Technical Data</h3>
              <p className="text-muted-foreground leading-relaxed">
                We may collect:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>IP addresses</li>
                <li>Browser type and version</li>
                <li>Access times and dates</li>
                <li>Pages viewed within our application</li>
              </ul>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              3. How We Use Your Information
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              We use collected information to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>
                <strong className="text-foreground">
                  Provide the Service:
                </strong>{" "}
                Process and deliver SMS messages, manage your account
              </li>
              <li>
                <strong className="text-foreground">
                  Improve the Service:
                </strong>{" "}
                Analyze usage patterns, fix bugs, develop new features
              </li>
              <li>
                <strong className="text-foreground">
                  Communicate with you:
                </strong>{" "}
                Send service updates, security alerts, support responses
              </li>
              <li>
                <strong className="text-foreground">Ensure security:</strong>{" "}
                Detect and prevent fraud, abuse, or unauthorized access
              </li>
              <li>
                <strong className="text-foreground">Process payments:</strong>{" "}
                Manage subscriptions and billing through our payment providers
              </li>
              <li>
                <strong className="text-foreground">
                  Comply with legal obligations:
                </strong>{" "}
                Respond to legal requests when required by law
              </li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              4. Data Storage and Security
            </h2>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">4.1 Data Location</h3>
              <p className="text-muted-foreground leading-relaxed">
                Your data is stored on servers located outside of Cuba, using
                reputable cloud infrastructure providers. This ensures reliable
                service availability and data protection.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">4.2 Security Measures</h3>
              <p className="text-muted-foreground leading-relaxed">
                We implement appropriate technical and organizational measures
                to protect your data:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>Encryption of data in transit (TLS/HTTPS)</li>
                <li>Secure password hashing</li>
                <li>Access controls and authentication</li>
                <li>Regular security assessments</li>
                <li>API key management and secure storage</li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">4.3 Data Retention</h3>
              <p className="text-muted-foreground leading-relaxed">
                We retain your data for as long as your account is active or as
                needed to provide the Service:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>
                  <strong className="text-foreground">Account data:</strong>{" "}
                  Retained until account deletion
                </li>
                <li>
                  <strong className="text-foreground">SMS logs:</strong>{" "}
                  Retained for a limited period for troubleshooting and billing
                  purposes
                </li>
                <li>
                  <strong className="text-foreground">Usage statistics:</strong>{" "}
                  May be retained in anonymized form for analytics
                </li>
              </ul>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">5. Data Sharing</h2>
            <p className="text-muted-foreground leading-relaxed">
              We do not sell your personal information. We may share data with:
            </p>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">5.1 Service Providers</h3>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                <li>
                  <strong className="text-foreground">
                    Payment processors:
                  </strong>{" "}
                  To handle subscription payments
                </li>
                <li>
                  <strong className="text-foreground">
                    Cloud infrastructure providers:
                  </strong>{" "}
                  To host and operate the Service
                </li>
                <li>
                  <strong className="text-foreground">
                    Email service providers:
                  </strong>{" "}
                  To send transactional emails
                </li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">5.2 Legal Requirements</h3>
              <p className="text-muted-foreground leading-relaxed">
                We may disclose information if required by law or in response to
                valid legal processes.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-medium">5.3 Business Transfers</h3>
              <p className="text-muted-foreground leading-relaxed">
                In the event of a merger, acquisition, or sale of assets, user
                data may be transferred. You will be notified of any such
                change.
              </p>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">6. Your Rights</h2>
            <p className="text-muted-foreground leading-relaxed">
              You have the right to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>
                <strong className="text-foreground">Access:</strong> Request a
                copy of your personal data
              </li>
              <li>
                <strong className="text-foreground">Correction:</strong> Update
                or correct inaccurate information
              </li>
              <li>
                <strong className="text-foreground">Deletion:</strong> Request
                deletion of your account and associated data
              </li>
              <li>
                <strong className="text-foreground">Export:</strong> Receive
                your data in a portable format
              </li>
              <li>
                <strong className="text-foreground">Objection:</strong> Object
                to certain processing of your data
              </li>
            </ul>
            <p className="text-muted-foreground leading-relaxed">
              To exercise these rights, please contact us at{" "}
              <a
                href={`mailto:${supportEmail}`}
                className="underline hover:text-foreground"
              >
                {supportEmail}
              </a>
              .
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">7. Cookies and Tracking</h2>
            <p className="text-muted-foreground leading-relaxed">
              We use essential cookies for:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Authentication and session management</li>
              <li>Security (CSRF protection)</li>
              <li>User preferences</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed">
              We do not use third-party advertising cookies or extensive
              tracking mechanisms.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">8. Third-Party Services</h2>
            <p className="text-muted-foreground leading-relaxed">
              Our Service may integrate with third-party services (payment
              providers, OAuth providers). These services have their own privacy
              policies, and we encourage you to review them.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">9. Children's Privacy</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service is not intended for users under 18 years of age. We do
              not knowingly collect information from children. If you become
              aware that a child has provided us with personal information,
              please contact us.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              10. International Data Transfers
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Your information may be transferred to and processed in countries
              other than your country of residence. These countries may have
              different data protection laws. By using the Service, you consent
              to such transfers.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              11. Changes to This Policy
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update this Privacy Policy from time to time. We will
              notify you of significant changes through the Service or via
              email. The "Last updated" date at the top indicates when the
              policy was last revised.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-semibold">12. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have questions about this Privacy Policy or our data
              practices, please contact us at{" "}
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
              By using {appName}, you acknowledge that you have read and
              understood this Privacy Policy.
            </p>
          </div>
        </article>
      </div>
    </div>
  )
}

export default Privacy
