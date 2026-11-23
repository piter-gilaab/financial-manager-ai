import type { Metadata } from "next";

export const metadata: Metadata = { title: "Overview" };

export default function OverviewLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
