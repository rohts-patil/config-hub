"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

type GoogleButtonText =
  | "signin_with"
  | "signup_with"
  | "continue_with"
  | "signin";

interface GoogleSignInButtonProps {
  disabled?: boolean;
  fallbackLabel: string;
  onCredential: (credential: string) => Promise<void>;
  text?: GoogleButtonText;
}

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

function GoogleMark() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M21.805 10.023H12v3.955h5.617c-.242 1.273-.967 2.352-2.061 3.077v2.555h3.338c1.954-1.8 3.08-4.452 2.91-7.587Z"
        fill="#4285F4"
      />
      <path
        d="M12 22c2.646 0 4.866-.873 6.49-2.39l-3.338-2.555c-.927.623-2.112.99-3.152.99-2.421 0-4.472-1.635-5.206-3.834H3.35v2.635A9.997 9.997 0 0 0 12 22Z"
        fill="#34A853"
      />
      <path
        d="M6.794 14.211A5.99 5.99 0 0 1 6.503 12c0-.768.132-1.515.291-2.211V7.154H3.35A9.999 9.999 0 0 0 2 12c0 1.61.385 3.13 1.35 4.846l3.444-2.635Z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.955c1.438 0 2.729.495 3.747 1.467l2.808-2.808C16.861 3.04 14.64 2 12 2a9.997 9.997 0 0 0-8.65 5.154l3.444 2.635C7.528 7.59 9.579 5.955 12 5.955Z"
        fill="#EA4335"
      />
    </svg>
  );
}

export function GoogleSignInButton({
  disabled = false,
  fallbackLabel,
  onCredential,
  text = "continue_with",
}: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    if (window.google?.accounts?.id) {
      setScriptReady(true);
    }
  }, []);

  useEffect(() => {
    if (!googleClientId || !scriptReady || !containerRef.current || !window.google) {
      return;
    }

    const container = containerRef.current;
    container.innerHTML = "";

    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: async (response) => {
        if (!response.credential) {
          toast.error("Google did not return a valid credential");
          return;
        }

        try {
          await onCredential(response.credential);
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Google sign-in failed";
          toast.error(message);
        }
      },
      context: text === "signup_with" ? "signup" : "signin",
      ux_mode: "popup",
    });

    window.google.accounts.id.renderButton(container, {
      type: "standard",
      theme: "outline",
      size: "large",
      text,
      shape: "rectangular",
      logo_alignment: "left",
      width: container.clientWidth || 320,
    });
  }, [onCredential, scriptReady, text]);

  if (!googleClientId) {
    return (
      <div className="space-y-2">
        <Button type="button" variant="outline" className="w-full" disabled>
          <GoogleMark />
          {fallbackLabel}
        </Button>
        <p className="text-center text-xs text-muted-foreground">
          Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to enable Google sign-in.
        </p>
      </div>
    );
  }

  return (
    <>
      <Script
        id="google-identity-services"
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
      />
      <div className={disabled ? "pointer-events-none opacity-60" : undefined}>
        <div ref={containerRef} className="flex min-h-10 w-full justify-center" />
      </div>
    </>
  );
}
