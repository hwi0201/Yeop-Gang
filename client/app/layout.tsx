import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Yeop-Gang",
  description: "EBS 인강 AI 튜터",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

