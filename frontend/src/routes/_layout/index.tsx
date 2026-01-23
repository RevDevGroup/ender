import { createFileRoute, Link } from "@tanstack/react-router"
import { MessageSquare, Smartphone, Webhook } from "lucide-react"
import QuotaCard from "@/components/Plans/QuotaCard"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { useDeviceList } from "@/hooks/useDeviceList"
import { useSMSList } from "@/hooks/useSMSList"
import { useWebhookList } from "@/hooks/useWebhookList"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Cloud",
      },
    ],
  }),
})

function StatCard({
  title,
  description,
  value,
  icon: Icon,
  href,
  isLoading,
}: {
  title: string
  description: string
  value: number | undefined
  icon: React.ElementType
  href: string
  isLoading: boolean
}) {
  return (
    <Link to={href}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">{title}</CardTitle>
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <p className="text-3xl font-bold">{value ?? 0}</p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}

function Dashboard() {
  const { user: currentUser } = useAuth()
  const { data: smsData, isLoading: smsLoading } = useSMSList()
  const { data: devicesData, isLoading: devicesLoading } = useDeviceList()
  const { data: webhooksData, isLoading: webhooksLoading } = useWebhookList()

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">
          Welcome back, nice to see you again!!!
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="SMS Messages"
          description="Total messages sent"
          value={smsData?.count}
          icon={MessageSquare}
          href="/sms"
          isLoading={smsLoading}
        />
        <StatCard
          title="Devices"
          description="Connected devices"
          value={devicesData?.count}
          icon={Smartphone}
          href="/devices"
          isLoading={devicesLoading}
        />
        <StatCard
          title="Webhooks"
          description="Active webhooks"
          value={webhooksData?.count}
          icon={Webhook}
          href="/webhooks"
          isLoading={webhooksLoading}
        />
      </div>

      <QuotaCard />
    </div>
  )
}
