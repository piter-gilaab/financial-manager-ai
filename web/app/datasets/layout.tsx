import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "Datasets",
    template: "%s — Financial Manager AI",
  },
};

export default function DatasetsLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
