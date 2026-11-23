import type { Metadata } from "next";

export const metadata: Metadata = { title: "Anomalies" };

export default function AnomaliesLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
