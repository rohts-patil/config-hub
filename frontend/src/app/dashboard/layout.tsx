"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { TopNav } from "@/components/top-nav";
import { useParams } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const orgId = params?.orgId as string | undefined;
  const productId = params?.productId as string | undefined;
  const configId = params?.configId as string | undefined;

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar orgId={orgId} productId={productId} configId={configId} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopNav />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}

