import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrailBlaze AI",
  description: "AI-powered outdoor guidance for Colorado trails",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          rel="stylesheet"
        />
        <link
          href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
          rel="stylesheet"
        />
        <link
          href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
