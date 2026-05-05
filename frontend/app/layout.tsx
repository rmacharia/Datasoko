import type { Metadata } from "next";

import { InternalHeader } from "@/components/internal-header";

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
        <script
          dangerouslySetInnerHTML={{
            __html: `(()=>{try{var s=localStorage.getItem("datasoko_theme");var p=s==="dark"||s==="light"||s==="system"?s:"system";var r=p==="system"?(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):p;document.documentElement.setAttribute("data-theme",r);document.documentElement.style.colorScheme=r;}catch(_){}})();`,
          }}
        />
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
