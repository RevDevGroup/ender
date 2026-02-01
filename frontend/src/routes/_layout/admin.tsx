import { createFileRoute } from "@tanstack/react-router"
import { Settings, Users } from "lucide-react"
import { Suspense, useState } from "react"

import type { UserPublic } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns, type UserTableData } from "@/components/Admin/columns"
import SystemSettings from "@/components/Admin/SystemSettings"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import { useUserListSuspense } from "@/hooks/useUserList"

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  head: () => ({
    meta: [
      {
        title: "Admin - FastAPI Cloud",
      },
    ],
  }),
})

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users } = useUserListSuspense()

  const tableData: UserTableData[] = (users?.data ?? []).map(
    (user: UserPublic) => ({
      ...user,
      isCurrentUser: currentUser?.id === user.id,
    }),
  )

  return <DataTable columns={columns} data={tableData} />
}

function UsersTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent />
    </Suspense>
  )
}

function Admin() {
  const [activeTab, setActiveTab] = useState("users")

  return (
    <div className="flex flex-col gap-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="users" className="gap-2">
              <Users className="h-4 w-4" />
              Users
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              Settings
            </TabsTrigger>
          </TabsList>

          {activeTab === "users" && <AddUser />}
        </div>

        <TabsContent value="users" className="mt-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold tracking-tight">Users</h1>
            <p className="text-muted-foreground">
              Manage user accounts and permissions
            </p>
          </div>
          <UsersTable />
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold tracking-tight">
              System Settings
            </h1>
            <p className="text-muted-foreground">
              Configure system-wide settings and payment options
            </p>
          </div>
          <SystemSettings />
        </TabsContent>
      </Tabs>
    </div>
  )
}
