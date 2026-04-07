"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { Flag } from "lucide-react";

function LoginPageContent() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const busy = loading || googleLoading;
  const inviteEmail = searchParams.get("email") || "";
  const inviteOrg = searchParams.get("org") || "";
  const inviteRole = searchParams.get("role") || "";
  const inviteToken = searchParams.get("invite_token") || "";
  const registerHref = useMemo(() => {
    const params = new URLSearchParams();
    if (inviteEmail) params.set("email", inviteEmail);
    if (inviteOrg) params.set("org", inviteOrg);
    if (inviteRole) params.set("role", inviteRole);
    if (inviteToken) params.set("invite_token", inviteToken);
    const qs = params.toString();
    return qs ? `/register?${qs}` : "/register";
  }, [inviteEmail, inviteOrg, inviteRole, inviteToken]);

  useEffect(() => {
    if (inviteEmail) {
      setEmail(inviteEmail);
    }
  }, [inviteEmail]);

  const inviteRoleLabel = inviteRole
    ? inviteRole
        .split("_")
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(" ")
    : "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password, inviteToken || undefined);
      router.push("/");
      toast.success("Welcome back!");
    } catch (err: any) {
      toast.error(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredential = async (credential: string) => {
    setGoogleLoading(true);
    try {
      await loginWithGoogle(credential, inviteToken || undefined);
      router.push("/");
      toast.success("Welcome back!");
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Flag className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl">Sign in to ConfigHub</CardTitle>
          <CardDescription>
            {inviteOrg
              ? `Sign in to accept your invite to ${inviteOrg}`
              : "Enter your credentials to access the dashboard"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {inviteOrg ? (
            <div className="mb-4 rounded-xl border border-border/70 bg-muted/50 p-3 text-left">
              <p className="text-sm font-medium">
                Use the invited email and your membership will be added
                automatically after sign-in.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant="outline">{inviteOrg}</Badge>
                {inviteRoleLabel ? (
                  <Badge variant="secondary">{inviteRoleLabel}</Badge>
                ) : null}
              </div>
            </div>
          ) : null}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
          <div className="my-4 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Or
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <GoogleSignInButton
            disabled={busy}
            text="signin_with"
            fallbackLabel="Continue with Google"
            onCredential={handleGoogleCredential}
          />
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link
              href={registerHref}
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign up
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthPageFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}

function AuthPageFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardContent className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    </div>
  );
}
