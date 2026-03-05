import type { Metadata } from "next";
import Script from "next/script";

import { InternalHeader } from "@/components/internal-header";
import { THEME_STORAGE_KEY } from "@/components/settings-provider";

import { Providers } from "./providers";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "DataSoko Internal Admin",
  description: "Internal admin console for ingestion, validation, and weekly report operations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script id="datasoko-theme-init" strategy="beforeInteractive">
          {`(() => {
            try {
              const stored = localStorage.getItem("${THEME_STORAGE_KEY}");
              const pref = stored === "dark" || stored === "light" || stored === "system" ? stored : "system";
              const resolved = pref === "system"
                ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
                : pref;
              document.documentElement.setAttribute("data-theme", resolved);
              document.documentElement.style.colorScheme = resolved;
            } catch (_) {}
          })();`}
        </Script>
      </head>
      <body suppressHydrationWarning>
        <Providers>
          <InternalHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}
