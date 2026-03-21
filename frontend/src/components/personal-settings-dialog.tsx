"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/contexts/theme-context";
import { MoonStar, Sparkles, SunMedium } from "lucide-react";

interface PersonalSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PersonalSettingsDialog({
  open,
  onOpenChange,
}: PersonalSettingsDialogProps) {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg overflow-hidden rounded-[1.6rem] border border-border/70 bg-card/95 p-0 shadow-[0_30px_70px_-40px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <div className="border-b border-border/70 bg-gradient-to-br from-primary/12 via-accent/10 to-secondary/12 px-6 py-5">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-4 w-4 text-primary" />
              Personal Settings
            </DialogTitle>
            <DialogDescription>
              Tune the dashboard to feel right for you. These preferences are
              saved on this device.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="rounded-[1.35rem] border border-border/70 bg-background/70 p-4 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <Label
                  htmlFor="dark-mode"
                  className="flex items-center gap-2 text-sm font-medium text-foreground"
                >
                  {isDark ? (
                    <MoonStar className="h-4 w-4 text-primary" />
                  ) : (
                    <SunMedium className="h-4 w-4 text-primary" />
                  )}
                  Dark Mode
                </Label>
                <p className="text-sm leading-6 text-muted-foreground">
                  Switch to a softer evening palette for late-night flag
                  wrangling.
                </p>
              </div>
              <Switch
                id="dark-mode"
                checked={isDark}
                onCheckedChange={(checked) =>
                  setTheme(checked ? "dark" : "light")
                }
                aria-label="Toggle dark mode"
              />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
