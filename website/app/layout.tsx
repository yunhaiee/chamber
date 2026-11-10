import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Footer, Header } from "@/components/Chrome";
import "./globals.css";

const base = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata: Metadata = {
  title: { default: "Chamber: on-device AI that earns its work", template: "%s | Chamber" },
  description: "One on-device AI shared by a law firm. Each model earns the work it can do, and privileged text never leaves.",
  icons: { icon: `${base}/logo.svg` },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Line-drawing starts hidden only when scripts can reveal it. */}
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body>
        <Header />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
