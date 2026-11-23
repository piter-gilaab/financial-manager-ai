import type { Metadata } from "next";

export const metadata: Metadata = { title: "Analysis" };

export default function AnalysisLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
