import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ETF 动量轮动交易系统",
  description: "基于动量因子的 ETF 轮动策略，结合双 Agent 协同完成智能调仓决策",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800">
        <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
            <span className="font-bold text-lg tracking-tight text-slate-900">ETF 动量轮动</span>
            <Link href="/" className="text-sm text-slate-500 transition hover:text-slate-900">
              仪表盘
            </Link>
            <Link href="/chat" className="text-sm text-slate-500 transition hover:text-slate-900">
              Agent 对话
            </Link>
            <Link href="/compare" className="text-sm text-slate-500 transition hover:text-slate-900">
              策略对比
            </Link>
          </div>
        </nav>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
