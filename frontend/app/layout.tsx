import type { Metadata, Viewport } from "next";
// @ts-ignore: allow side-effect CSS import without type declarations
import "./globals.css";

export const metadata: Metadata = {
  title: "DocChat — AI Document Assistant",
  description:
    "Chat with your documents using advanced AI. Get instant answers, summaries, and insights.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: "/apple-icon.png",
    shortcut: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#f4f6ff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ height: "100%" }}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
        {/* Explicit favicon links as fallback for all browsers */}
        <link rel="icon" type="image/x-icon" href="/favicon.ico" />
        <link rel="icon" type="image/png" href="/icon.png" />
        <link rel="apple-touch-icon" href="/apple-icon.png" />
      </head>
      <body
        className="antialiased text-slate-900 bg-slate-50"
        style={{
          minHeight: "100%",
          margin: 0,
          padding: 0,
          WebkitTapHighlightColor: "transparent" as any,
        }}
      >
        {children}
      </body>
    </html>
  );
}