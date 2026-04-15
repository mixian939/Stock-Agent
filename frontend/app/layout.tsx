import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ETF 动量轮动交易系统",
  description: "Agent 量化交易系统 - 仪表盘 & 聊天",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800">
        <nav className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
            <span className="font-bold text-lg tracking-tight text-slate-900">ETF 动量轮动</span>
            <Link href="/" className="text-sm text-slate-500 hover:text-slate-900 transition">
              仪表盘
            </Link>
            <Link href="/chat" className="text-sm text-slate-500 hover:text-slate-900 transition">
              Agent 聊天
            </Link>
            <Link href="/compare" className="text-sm text-slate-500 hover:text-slate-900 transition">
              策略对比
            </Link>
          </div>
        </nav>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
