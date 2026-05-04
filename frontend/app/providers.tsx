"use client";

import { AuthProvider } from "@/components/auth-provider";
import { OrgProvider } from "@/components/org-provider";
import { SettingsProvider } from "@/components/settings-provider";
import { ToastProvider } from "@/components/toast-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SettingsProvider>
      <AuthProvider>
        <OrgProvider>
          <ToastProvider>{children}</ToastProvider>
        </OrgProvider>
      </AuthProvider>
    </SettingsProvider>
  );
}
