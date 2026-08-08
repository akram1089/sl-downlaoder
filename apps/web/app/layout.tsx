import type { Metadata } from "next";
import { IBM_Plex_Sans, Syne } from "next/font/google";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["500", "600", "700", "800"],
});

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-plex",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "StreamLine — Media Downloader",
  description: "Production-grade multi-source media downloads for SpikeIQ.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${syne.variable} ${plex.variable}`}>
      <body className="font-sans antialiased">
        <div className="grain fixed inset-0 z-50" aria-hidden />
        {children}
      </body>
    </html>
  );
}
