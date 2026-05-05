"use client";

import { AuthProvider } from "@/components/auth-provider";
import { OrgProvider } from "@/components/org-provider";
import { RouteGuard } from "@/components/route-guard";
import { SettingsProvider } from "@/components/settings-provider";
import { ToastProvider } from "@/components/toast-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SettingsProvider>
      <AuthProvider>
        <OrgProvider>
          <ToastProvider>
            <RouteGuard>{children}</RouteGuard>
          </ToastProvider>
        </OrgProvider>
      </AuthProvider>
    </SettingsProvider>
  );
}
