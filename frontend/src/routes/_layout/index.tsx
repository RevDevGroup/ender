import { createFileRoute, Link } from "@tanstack/react-router"
import {
  CheckCircle2,
  ChevronRight,
  Clock,
  Globe,
  Key,
  MessageSquare,
  MessageSquareText,
  Server,
  Smartphone,
  Webhook,
  Zap,
} from "lucide-react"

import QuotaCard from "@/components/Plans/QuotaCard"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useApiKeyList } from "@/hooks/useApiKeyList"
import useAppConfig from "@/hooks/useAppConfig"
import useAuth from "@/hooks/useAuth"
import { useDeviceList } from "@/hooks/useDeviceList"
import { useSMSList } from "@/hooks/useSMSList"
import { useWebhookList } from "@/hooks/useWebhookList"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
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
      <Card className="cursor-pointer">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <Icon className="h-5 w-5 text-[#2dd4a8]" />
            {title}
          </CardTitle>
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

function StatusIndicator({
  status,
  label,
}: {
  status: "operational" | "degraded" | "down"
  label: string
}) {
  const statusConfig = {
    operational: {
      color: "bg-green-500",
      text: "Operational",
      textColor: "text-green-600 dark:text-green-400",
    },
    degraded: {
      color: "bg-yellow-500",
      text: "Degraded",
      textColor: "text-yellow-600 dark:text-yellow-400",
    },
    down: {
      color: "bg-red-500",
      text: "Down",
      textColor: "text-red-600 dark:text-red-400",
    },
  }

  const config = statusConfig[status]

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${config.color} animate-pulse`}
        />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className={`text-xs font-medium ${config.textColor}`}>
        {config.text}
      </span>
    </div>
  )
}

function SystemStatusCard() {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-3">
          <Zap className="h-5 w-5 text-[#2dd4a8]" />
          System Status
        </CardTitle>
        <Badge variant="secondary" className="text-xs">
          Live
        </Badge>
      </CardHeader>
      <CardContent className="space-y-1">
        <StatusIndicator status="operational" label="API Services" />
        <StatusIndicator status="operational" label="SMS Gateway" />
        <StatusIndicator status="operational" label="Webhooks" />
      </CardContent>
    </Card>
  )
}

function QuickInfoCard({
  devicesOnline,
  apiKeysActive,
  isLoading,
}: {
  devicesOnline: number
  apiKeysActive: number
  isLoading: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <Clock className="h-5 w-5 text-[#2dd4a8]" />
          Quick Info
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Devices Online
            </span>
          </div>
          {isLoading ? (
            <Skeleton className="h-5 w-8" />
          ) : (
            <Badge variant="outline">{devicesOnline}</Badge>
          )}
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Active API Keys
            </span>
          </div>
          {isLoading ? (
            <Skeleton className="h-5 w-8" />
          ) : (
            <Badge variant="outline">{apiKeysActive}</Badge>
          )}
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">API Version</span>
          </div>
          <Badge variant="secondary">v1</Badge>
        </div>
      </CardContent>
    </Card>
  )
}

function GettingStartedCard() {
  return (
    <Link to="/devices">
      <Card className="cursor-pointer group">
        <CardHeader className="flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-[#2dd4a8]/10 p-2">
              <CheckCircle2 className="h-5 w-5 text-[#2dd4a8]" />
            </div>
            <div>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>
                Set up your first device and start sending SMS
              </CardDescription>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:translate-x-1 transition-transform" />
        </CardHeader>
      </Card>
    </Link>
  )
}

function Dashboard() {
  const { user: currentUser } = useAuth()
  const { config } = useAppConfig()
  const { data: smsData, isLoading: smsLoading } = useSMSList("outgoing")
  const { data: incomingSmsData, isLoading: incomingSmsLoading } =
    useSMSList("incoming")
  const { data: devicesData, isLoading: devicesLoading } = useDeviceList()
  const { data: webhooksData, isLoading: webhooksLoading } = useWebhookList()
  const { data: apiKeysData, isLoading: apiKeysLoading } = useApiKeyList()

  return (
    <div className="flex flex-col gap-8">
      <title>{`Dashboard - ${config.appName}`}</title>
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">
          Welcome back, nice to see you again!
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="SMS Sent"
          description="Total messages sent"
          value={smsData?.count}
          icon={MessageSquare}
          href="/sms"
          isLoading={smsLoading}
        />
        <StatCard
          title="SMS Received"
          description="Total messages received"
          value={incomingSmsData?.count}
          icon={MessageSquareText}
          href="/sms"
          isLoading={incomingSmsLoading}
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

      {/* Main content area with sidebar layout */}
      <div className="grid gap-4 lg:grid-cols-4">
        {/* Left side - System info (3/4 width) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <SystemStatusCard />
            <QuickInfoCard
              devicesOnline={devicesData?.count ?? 0}
              apiKeysActive={apiKeysData?.count ?? 0}
              isLoading={devicesLoading || apiKeysLoading}
            />
          </div>
          <GettingStartedCard />
        </div>

        {/* Right side - Quota card (1/4 width) */}
        <div className="lg:col-span-1">
          <QuotaCard />
        </div>
      </div>
    </div>
  )
}
