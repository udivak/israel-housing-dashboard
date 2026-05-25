import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { Header } from "@/components/layout/Header";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Israel Housing — modeled, mapped, priced",
  description:
    "AI-powered intelligence platform for the Israeli real-estate market: live listings, seven models, interactive maps.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-[var(--bg)] font-sans text-[var(--fg)] antialiased`}
      >
        <QueryProvider>
          <Header />
          <main className="mx-auto max-w-7xl">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
