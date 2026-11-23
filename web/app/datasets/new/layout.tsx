import type { Metadata } from "next";

export const metadata: Metadata = { title: "Add Dataset" };

export default function AddDatasetLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
