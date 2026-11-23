import type { Metadata } from "next";

export const metadata: Metadata = { title: "Dataset" };

export default function DatasetLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
