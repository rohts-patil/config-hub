"use client";

import { useEffect } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { TopNav } from "@/components/top-nav";
import { setLastOrgId, setLastProductId } from "@/lib/dashboard-context";
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

  useEffect(() => {
    if (!orgId) return;
    setLastOrgId(orgId);
  }, [orgId]);

  useEffect(() => {
    if (!orgId || !productId) return;
    setLastProductId(orgId, productId);
  }, [orgId, productId]);

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-transparent">
        <Sidebar orgId={orgId} productId={productId} configId={configId} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopNav />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-7xl p-6 md:p-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
