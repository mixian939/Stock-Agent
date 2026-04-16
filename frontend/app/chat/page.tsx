"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "您好，我是主交易 Agent（GPT-5.4）。您可以就策略逻辑、当前持仓、绩效表现及 ETF 轮动机制进行提问。在回测模式下，系统将同时接入金融子 Agent（Fin-R1）提供辅助分析。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const reply = await api.chat(text);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "请求失败，请确认后端服务是否正常运行。" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(20,83,45,0.12),_transparent_26%),linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)]">
      <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-6">
        <section className="rounded-[30px] border border-emerald-100 bg-[linear-gradient(135deg,_rgba(15,23,42,0.98),_rgba(20,83,45,0.92)_55%,_rgba(14,116,144,0.86))] p-5 text-white shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
          <div className="text-xs uppercase tracking-[0.22em] text-emerald-200/80">Agent Dialog</div>
          <h1 className="mt-2 text-2xl font-semibold">交易 Agent 对话终端</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-50/90">
            与主 Agent（GPT-5.4）直接交互。调仓决策时，主 Agent 将参考金融子 Agent（Fin-R1）的分析建议，并按 60/40 权重综合评分后做出最终裁决。
          </p>
        </section>

        <div className="flex h-[calc(100vh-14rem)] flex-col rounded-[30px] border border-white/60 bg-white/86 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="border-b border-slate-200/80 px-5 py-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Conversation</div>
            <div className="mt-1 text-sm text-slate-600">示例问题：当前策略的轮动逻辑、某只 ETF 的持仓依据、近期绩效分析、调仓决策思路。</div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.map((message, i) => (
              <div key={i} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    message.role === "user"
                      ? "bg-slate-950 text-white shadow-[0_12px_30px_rgba(15,23,42,0.18)]"
                      : "border border-slate-200 bg-white text-slate-700 shadow-sm"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-400 shadow-sm animate-pulse">
                  正在分析...
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-slate-200/80 p-4">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-emerald-500"
                placeholder="输入问题，如：当前持仓的调仓依据是什么？"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                disabled={loading}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="rounded-2xl bg-emerald-700 px-5 py-3 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                发送
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
