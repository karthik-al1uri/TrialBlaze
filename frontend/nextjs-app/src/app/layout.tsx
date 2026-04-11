import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrailBlaze AI",
  description: "AI-powered outdoor guidance for Colorado trails",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}