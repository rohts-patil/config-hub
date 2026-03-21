"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useParams, usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  getLastProductId,
  setLastOrgId,
  setLastProductId,
} from "@/lib/dashboard-context";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { PersonalSettingsDialog } from "@/components/personal-settings-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, Settings2 } from "lucide-react";
import { toast } from "sonner";

const PRODUCT_SECTION_ROUTES = new Set([
  "environments",
  "segments",
  "tags",
  "sdk-keys",
]);

function getProductDestination(
  pathname: string,
  nextOrgId: string,
  nextProductId: string
) {
  const segments = pathname.split("/").filter(Boolean);
  const productTail = segments.slice(3);

  if (productTail.length === 0) {
    return `/dashboard/${nextOrgId}/${nextProductId}`;
  }

  if (PRODUCT_SECTION_ROUTES.has(productTail[0])) {
    return `/dashboard/${nextOrgId}/${nextProductId}/${productTail[0]}`;
  }

  return `/dashboard/${nextOrgId}/${nextProductId}`;
}

function getOrgDestination(
  pathname: string,
  nextOrgId: string,
  nextProductId?: string | null
) {
  const segments = pathname.split("/").filter(Boolean);
  const orgTail = segments.slice(2);

  if (orgTail[0] === "audit-log") {
    return `/dashboard/${nextOrgId}/audit-log`;
  }

  if (orgTail[0] === "webhooks") {
    return `/dashboard/${nextOrgId}/webhooks`;
  }

  if (nextProductId) {
    return getProductDestination(pathname, nextOrgId, nextProductId);
  }

  return `/dashboard/${nextOrgId}`;
}

export function TopNav() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const orgId = params?.orgId as string | undefined;
  const productId = params?.productId as string | undefined;
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [productsLoading, setProductsLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const selectedOrg = orgs.find((org) => org.id === orgId);
  const selectedProduct = products.find((product) => product.id === productId);

  const initials =
    user?.name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "U";

  useEffect(() => {
    let cancelled = false;

    const loadOrgs = async () => {
      try {
        const data = await api.organizations.list();
        if (!cancelled) setOrgs(data);
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) setOrgsLoading(false);
      }
    };

    loadOrgs();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!orgId) {
      setProducts([]);
      setProductsLoading(false);
      return;
    }

    let cancelled = false;
    setProductsLoading(true);

    const loadProducts = async () => {
      try {
        const data = await api.products.list(orgId);
        if (!cancelled) setProducts(data);
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) setProductsLoading(false);
      }
    };

    loadProducts();

    return () => {
      cancelled = true;
    };
  }, [orgId]);

  const handleOrgChange = async (nextOrgId: string | null) => {
    if (!nextOrgId || nextOrgId === orgId) return;

    try {
      const nextProducts = await api.products.list(nextOrgId);
      setLastOrgId(nextOrgId);
      setProducts(nextProducts);

      const rememberedProductId = getLastProductId(nextOrgId);
      const resolvedProductId =
        nextProducts.find((product) => product.id === rememberedProductId)
          ?.id || (nextProducts.length === 1 ? nextProducts[0].id : null);

      if (resolvedProductId) {
        setLastProductId(nextOrgId, resolvedProductId);
      }

      router.push(getOrgDestination(pathname, nextOrgId, resolvedProductId));
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleProductChange = (nextProductId: string | null) => {
    if (!orgId || !nextProductId || nextProductId === productId) return;
    setLastProductId(orgId, nextProductId);
    router.push(getProductDestination(pathname, orgId, nextProductId));
  };

  return (
    <>
      <header className="flex h-16 items-center justify-between border-b border-border/70 bg-background/65 px-6 backdrop-blur-xl">
        <div className="flex min-w-0 items-center gap-4">
          <div className="hidden items-center gap-2 md:flex">
            <Select
              value={orgId}
              onValueChange={handleOrgChange}
              disabled={orgsLoading || orgs.length === 0}
            >
              <SelectTrigger className="h-10 min-w-[180px] rounded-2xl border-border/70 bg-background/75 px-3 shadow-sm">
                <span className="truncate">
                  {selectedOrg?.name || "Select organization"}
                </span>
              </SelectTrigger>
              <SelectContent align="start">
                {orgs.map((org) => (
                  <SelectItem key={org.id} value={org.id}>
                    {org.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={productId}
              onValueChange={handleProductChange}
              disabled={!orgId || productsLoading || products.length === 0}
            >
              <SelectTrigger className="h-10 min-w-[180px] rounded-2xl border-border/70 bg-background/75 px-3 shadow-sm">
                <span className="truncate">
                  {selectedProduct?.name ||
                    (orgId
                      ? productsLoading
                        ? "Loading products..."
                        : "Select product"
                      : "Choose an organization")}
                </span>
              </SelectTrigger>
              <SelectContent align="start">
                {products.map((product) => (
                  <SelectItem key={product.id} value={product.id}>
                    {product.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button
              variant="ghost"
              className="relative h-10 w-10 overflow-hidden rounded-full border border-border/70 bg-card/80 shadow-sm hover:bg-card"
            >
              <Avatar className="h-10 w-10 after:hidden">
                <AvatarFallback className="bg-accent text-foreground text-[0.8rem] font-semibold tracking-wide">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <div className="px-2 py-1.5">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setSettingsOpen(true)}>
              <Settings2 className="mr-2 h-4 w-4" />
              Personal settings
            </DropdownMenuItem>
            <DropdownMenuItem onClick={logout} className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>
      <PersonalSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </>
  );
}
