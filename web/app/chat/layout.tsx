import type { Metadata } from "next";

export const metadata: Metadata = { title: "Ask Financial Manager" };

export default function ChatLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
