"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Flag,
  Building2,
  Package,
  Layers,
  Users,
  Tag,
  Key,
  ScrollText,
  Webhook,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const mainNav: NavItem[] = [
  { label: "Organizations", href: "/dashboard", icon: Building2 },
];

interface SidebarProps {
  orgId?: string;
  productId?: string;
  configId?: string;
}

export function Sidebar({ orgId, productId, configId }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const contextNav: NavItem[] = [];

  if (orgId) {
    contextNav.push({
      label: "Products",
      href: `/dashboard/${orgId}`,
      icon: Package,
    });
  }
  if (orgId && productId) {
    contextNav.push(
      {
        label: "Configs",
        href: `/dashboard/${orgId}/${productId}`,
        icon: Layers,
      },
      {
        label: "Environments",
        href: `/dashboard/${orgId}/${productId}/environments`,
        icon: Settings,
      },
      {
        label: "Segments",
        href: `/dashboard/${orgId}/${productId}/segments`,
        icon: Users,
      },
      {
        label: "Tags",
        href: `/dashboard/${orgId}/${productId}/tags`,
        icon: Tag,
      }
    );
  }
  if (orgId && productId) {
    contextNav.push({
      label: "SDK Keys",
      href: `/dashboard/${orgId}/${productId}/sdk-keys`,
      icon: Key,
    });
  }
  if (orgId && productId && configId) {
    contextNav.push({
      label: "Feature Flags",
      href: `/dashboard/${orgId}/${productId}/${configId}`,
      icon: Flag,
    });
  }
  if (orgId) {
    contextNav.push(
      {
        label: "Audit Log",
        href: `/dashboard/${orgId}/audit-log`,
        icon: ScrollText,
      },
      { label: "Webhooks", href: `/dashboard/${orgId}/webhooks`, icon: Webhook }
    );
  }

  const allNav = [...mainNav, ...contextNav];

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!collapsed && (
          <Link
            href="/dashboard"
            className="flex items-center gap-2 font-semibold"
          >
            <Flag className="h-5 w-5 text-primary" />
            <span>ConfigHub</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {allNav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
