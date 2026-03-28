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
  { label: "Organizations", href: "/dashboard?view=all", icon: Building2 },
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
        "relative flex h-screen flex-col overflow-hidden border-r border-sidebar-border/70 bg-sidebar/85 text-sidebar-foreground shadow-[22px_0_50px_-36px_rgba(144,89,56,0.4)] backdrop-blur-xl transition-all duration-300",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,184,137,0.26),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(114,196,180,0.2),transparent_28%)]" />
      <div className="relative flex h-16 items-center justify-between border-b border-sidebar-border/60 px-4">
        {!collapsed && (
          <Link
            href="/dashboard?view=all"
            className="flex items-center gap-3 font-semibold"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-inner">
              <Flag className="h-5 w-5" />
            </span>
            <div className="leading-tight">
              <span className="block text-[0.72rem] uppercase tracking-[0.24em] text-sidebar-foreground/55">
                Cozy Flags
              </span>
              <span className="block text-base text-sidebar-foreground">
                ConfigHub
              </span>
            </div>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-2xl bg-background/55 dark:bg-background/75"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      <nav className="relative flex-1 space-y-1.5 overflow-y-auto p-3">
        {allNav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm transition-all duration-200",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-[0_18px_34px_-24px_rgba(214,120,71,0.75)]"
                  : "text-sidebar-foreground/72 hover:bg-sidebar-accent/55 hover:text-sidebar-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-primary" : "text-sidebar-foreground/60"
                )}
              />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
