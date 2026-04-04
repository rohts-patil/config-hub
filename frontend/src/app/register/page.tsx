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

function RegisterPageContent() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { loginWithGoogle, register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const busy = loading || googleLoading;
  const inviteEmail = searchParams.get("email") || "";
  const inviteOrg = searchParams.get("org") || "";
  const inviteRole = searchParams.get("role") || "";
  const loginHref = useMemo(() => {
    const params = new URLSearchParams();
    if (inviteEmail) params.set("email", inviteEmail);
    if (inviteOrg) params.set("org", inviteOrg);
    if (inviteRole) params.set("role", inviteRole);
    const qs = params.toString();
    return qs ? `/login?${qs}` : "/login";
  }, [inviteEmail, inviteOrg, inviteRole]);

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
      await register(email, name, password);
      router.push("/");
      toast.success("Account created!");
    } catch (err: any) {
      toast.error(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredential = async (credential: string) => {
    setGoogleLoading(true);
    try {
      await loginWithGoogle(credential);
      router.push("/");
      toast.success("Welcome to ConfigHub!");
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
          <CardTitle className="text-2xl">Create an account</CardTitle>
          <CardDescription>
            {inviteOrg
              ? `Join ${inviteOrg}${inviteRoleLabel ? ` as ${inviteRoleLabel}` : ""}`
              : "Get started with ConfigHub"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {inviteOrg ? (
            <div className="mb-4 rounded-xl border border-border/70 bg-muted/50 p-3 text-left">
              <p className="text-sm font-medium">
                This invite will be accepted automatically after signup.
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
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={busy}
                required
              />
            </div>
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
                placeholder="Min 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
                required
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {loading ? "Creating account..." : "Create Account"}
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
            text="signup_with"
            fallbackLabel="Sign up with Google"
            onCredential={handleGoogleCredential}
          />
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              href={loginHref}
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<AuthPageFallback />}>
      <RegisterPageContent />
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
