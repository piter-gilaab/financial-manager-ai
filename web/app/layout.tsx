import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { WorkspaceProvider } from "@/components/workspace-provider";

export const metadata: Metadata = {
  title: {
    default: "Financial Manager AI",
    template: "%s — Financial Manager AI",
  },
  description: "Local institutional financial analysis workspace",
  applicationName: "Financial Manager AI",
  icons: { icon: "/icon.svg" },
  other: {
    "page-type": "software",
    "site-kind": "software",
  },
};

export const viewport: Viewport = { themeColor: "#f4f5f2" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-type="software">
      <body>
        <WorkspaceProvider>
          <AppShell>{children}</AppShell>
        </WorkspaceProvider>
      </body>
    </html>
  );
}
