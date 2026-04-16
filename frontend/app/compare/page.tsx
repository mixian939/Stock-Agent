"use client";

import { Fragment, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  CompareStatus,
  CompareNavPoint,
  CompareMetrics,
  DecisionComparison,
  CompareTrades,
  Trade,
} from "@/lib/api";

function formatDate(d: unknown) {
  const s = String(d);
  if (s.length === 8) return `${s.slice(4, 6)}-${s.slice(6)}`;
  return s;
}

function formatWeights(weights: Record<string, number>, nameMap?: Record<string, string>) {
  return Object.entries(weights)
    .filter(([, w]) => w > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([code, w]) => `${nameMap?.[code] ?? code.split(".")[0]} ${(w * 100).toFixed(0)}%`)
    .join(", ");
}

function MetricPair({ label, algoVal, aiVal }: { label: string; algoVal: string; aiVal: string | null }) {
  return (
    <div className="rounded-3xl border border-white/60 bg-white/88 p-4 shadow-[0_14px_40px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-indigo-50 p-3">
          <div className="text-[10px] uppercase tracking-[0.16em] text-indigo-500">算法基线</div>
          <div className="mt-1 text-lg font-semibold text-indigo-700">{algoVal}</div>
        </div>
        <div className="rounded-2xl bg-amber-50 p-3">
          <div className="text-[10px] uppercase tracking-[0.16em] text-amber-500">协同决策</div>
          <div className="mt-1 text-lg font-semibold text-amber-700">{aiVal ?? "—"}</div>
        </div>
      </div>
    </div>
  );
}

function fmtPct(v: number | undefined) {
  if (v === undefined) return null;
  return `${v >= 0 ? "+" : ""}${v}%`;
}

function TradeTable({ trades }: { trades: Trade[] }) {
  if (!trades.length) return <div className="py-4 text-center text-sm text-slate-400">尚无交易记录</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-slate-500">
            <th className="px-2 py-2 text-left">日期</th>
            <th className="px-2 py-2 text-left">ETF</th>
            <th className="px-2 py-2 text-left">方向</th>
            <th className="px-2 py-2 text-right">股数</th>
            <th className="px-2 py-2 text-right">价格</th>
            <th className="px-2 py-2 text-right">金额</th>
          </tr>
        </thead>
        <tbody>
          {trades.slice(-30).reverse().map((trade, i) => (
            <tr key={i} className="border-b border-slate-100 hover:bg-slate-50/60">
              <td className="px-2 py-1.5 font-mono text-xs text-slate-600">{formatDate(trade.date)}</td>
              <td className="px-2 py-1.5 text-slate-700">{trade.name}</td>
              <td className={`px-2 py-1.5 font-medium ${trade.direction === "BUY" ? "text-emerald-600" : "text-rose-600"}`}>
                {trade.direction === "BUY" ? "买入" : "卖出"}
              </td>
              <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.shares.toLocaleString()}</td>
              <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.price.toFixed(3)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.amount.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScoreChips({ scores, title, tone, nameMap }: { scores?: Record<string, number>; title: string; tone: "sub" | "main" | "weighted"; nameMap?: Record<string, string> }) {
  const classes =
    tone === "sub"
      ? "bg-emerald-100 text-emerald-700"
      : tone === "main"
        ? "bg-amber-100 text-amber-700"
        : "bg-slate-200 text-slate-700";
  const sorted = Object.entries(scores ?? {}).sort(([, a], [, b]) => b - a).slice(0, 5);
  if (!sorted.length) return null;
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">{title}</div>
      <div className="flex flex-wrap gap-2">
        {sorted.map(([code, score]) => (
          <span key={code} className={`rounded-full px-2.5 py-1 text-xs ${classes}`}>
            {nameMap?.[code] ?? code.split(".")[0]} {score.toFixed(1)}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [status, setStatus] = useState<CompareStatus | null>(null);
  const [navData, setNavData] = useState<CompareNavPoint[]>([]);
  const [metrics, setMetrics] = useState<CompareMetrics | null>(null);
  const [decisions, setDecisions] = useState<DecisionComparison[]>([]);
  const [trades, setTrades] = useState<CompareTrades | null>(null);
  const [loading, setLoading] = useState(true);
  const [tradeTab, setTradeTab] = useState<"algo" | "ai">("algo");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  async function refreshData() {
    try {
      const [s, n, m, d, t] = await Promise.all([
        api.compareStatus(),
        api.compareNav(),
        api.compareMetrics(),
        api.compareDecisions(),
        api.compareTrades(),
      ]);
      setStatus(s);
      setNavData(n);
      setMetrics(m);
      setDecisions(d);
      setTrades(t);
    } catch {
      // ignore
    }
    setLoading(false);
  }

  useEffect(() => {
    let active = true;

    const loadInitialData = async () => {
      try {
        const [s, n, m, d, t] = await Promise.all([
          api.compareStatus(),
          api.compareNav(),
          api.compareMetrics(),
          api.compareDecisions(),
          api.compareTrades(),
        ]);
        if (!active) return;
        setStatus(s);
        setNavData(n);
        setMetrics(m);
        setDecisions(d);
        setTrades(t);
      } catch {
        // ignore
      }
      if (active) setLoading(false);
    };

    void loadInitialData();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!status || status.agent_status === "completed" || status.agent_status === "failed") return;
    const timer = setInterval(async () => {
      try {
        const s = await api.compareStatus();
        setStatus(s);
        if (s.agent_status === "completed") {
          void refreshData();
        }
      } catch {
        // ignore
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [status]);

  const toggleRow = (date: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-lg text-slate-400 animate-pulse">加载中...</div>
      </div>
    );
  }

  const algo = metrics?.algo;
  const ai = metrics?.ai;
  const hasAi = status?.agent_status === "completed" && ai != null;

  const nameMap: Record<string, string> = {};
  for (const d of decisions) {
    for (const r of d.momentum_rankings) nameMap[r.ts_code] = r.name;
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(245,158,11,0.1),_transparent_24%),linear-gradient(180deg,_#fffdf8_0%,_#f8fafc_100%)]">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
        <section className="rounded-[32px] border border-amber-100 bg-[linear-gradient(135deg,_rgba(15,23,42,0.98),_rgba(120,53,15,0.94)_60%,_rgba(245,158,11,0.82))] p-6 text-white shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
          <div className="text-xs uppercase tracking-[0.22em] text-amber-200/80">Strategy Compare</div>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">算法基线 vs 双 Agent 协同决策</h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-amber-50/90">
            算法基线采用纯动量因子轮动策略；双 Agent 模式下，金融子 Agent（Fin-R1）先输出市场分析与仓位建议，主 Agent（GPT-5.4）再综合评分完成最终调仓，权重配比为 Fin-R1 60% / GPT-5.4 40%。
          </p>
        </section>

        {status && status.agent_status !== "completed" && (
          <div className={`rounded-3xl p-4 text-sm ${
            status.agent_status === "failed"
              ? "border border-rose-200 bg-rose-50 text-rose-700"
              : "border border-amber-200 bg-amber-50 text-amber-700"
          }`}>
            {status.agent_status === "pending" && "双 Agent 回测等待启动..."}
            {status.agent_status === "running" && "双 Agent 回测运行中，完成后自动刷新对比数据..."}
            {status.agent_status === "failed" && `双 Agent 回测异常：${status.agent_error}`}
          </div>
        )}

        {algo && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            <MetricPair label="总收益率" algoVal={fmtPct(algo.total_return)!} aiVal={fmtPct(ai?.total_return)} />
            <MetricPair label="年化收益" algoVal={fmtPct(algo.annualized_return)!} aiVal={fmtPct(ai?.annualized_return)} />
            <MetricPair label="最大回撤" algoVal={`${algo.max_drawdown}%`} aiVal={ai ? `${ai.max_drawdown}%` : null} />
            <MetricPair label="夏普比率" algoVal={`${algo.sharpe_ratio}`} aiVal={ai ? `${ai.sharpe_ratio}` : null} />
            <MetricPair label="交易次数" algoVal={`${algo.total_trades}`} aiVal={ai ? `${ai.total_trades}` : null} />
          </div>
        )}

        <div className="rounded-[28px] border border-white/60 bg-white/90 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">净值对比曲线</h2>
          <div className="mt-4 h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={navData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} domain={["dataMin - 10000", "dataMax + 10000"]} tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}万`} />
                <Tooltip
                  contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 16 }}
                  labelFormatter={formatDate}
                  formatter={(v, name) => [`${Number(v).toLocaleString()} 元`, name === "algo_nav" ? "算法基线" : "协同决策"]}
                />
                <Legend formatter={(v: string) => (v === "algo_nav" ? "算法基线" : "协同决策")} />
                <Line type="monotone" dataKey="algo_nav" stroke="#4f46e5" strokeWidth={2.2} dot={false} name="algo_nav" />
                {hasAi && <Line type="monotone" dataKey="ai_nav" stroke="#f59e0b" strokeWidth={2.2} dot={false} name="ai_nav" />}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/60 bg-white/90 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">回撤对比曲线</h2>
          <div className="mt-4 h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={navData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                <Tooltip
                  contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 16 }}
                  labelFormatter={formatDate}
                  formatter={(v, name) => [`${(Number(v) * 100).toFixed(2)}%`, name === "algo_drawdown" ? "算法基线" : "协同决策"]}
                />
                <Legend formatter={(v: string) => (v === "algo_drawdown" ? "算法基线回撤" : "协同决策回撤")} />
                <Area type="monotone" dataKey="algo_drawdown" stroke="#818cf8" fill="#c7d2fe40" strokeWidth={1.6} name="algo_drawdown" />
                {hasAi && <Area type="monotone" dataKey="ai_drawdown" stroke="#f59e0b" fill="#fde68a50" strokeWidth={1.6} name="ai_drawdown" />}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/60 bg-white/90 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">调仓决策对比</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="w-24 px-3 py-2 text-left">日期</th>
                  <th className="px-3 py-2 text-left">算法基线配置</th>
                  <th className="px-3 py-2 text-left">协同决策配置</th>
                  <th className="w-24 px-3 py-2 text-center">执行状态</th>
                  <th className="w-16 px-3 py-2 text-center">是否一致</th>
                  <th className="w-16 px-3 py-2 text-center">操作</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((decision) => {
                  const isExpanded = expandedRows.has(decision.date);
                  const rowBg = decision.decisions_match ? "" : "bg-amber-50/70";
                  return (
                    <Fragment key={decision.date}>
                      <tr className={`border-b border-slate-100 hover:bg-slate-50/60 ${rowBg}`}>
                        <td className="px-3 py-2 font-mono text-xs text-slate-600">{formatDate(decision.date)}</td>
                        <td className="px-3 py-2 text-xs text-slate-700">{decision.algo ? formatWeights(decision.algo.target_weights, nameMap) : "—"}</td>
                        <td className="px-3 py-2 text-xs text-slate-700">
                          {decision.ai ? formatWeights(decision.ai.target_weights, nameMap) : hasAi ? "—" : "待完成"}
                        </td>
                        <td className="px-3 py-2 text-center text-xs text-slate-600">
                          {decision.ai?.execution_status ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {decision.ai == null ? (
                            <span className="text-slate-300">—</span>
                          ) : decision.decisions_match ? (
                            <span className="text-xs text-emerald-600">一致</span>
                          ) : (
                            <span className="text-xs font-medium text-amber-600">不同</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <button onClick={() => toggleRow(decision.date)} className="text-xs text-indigo-500 hover:text-indigo-700">
                            {isExpanded ? "收起" : "详情"}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className={rowBg}>
                          <td colSpan={6} className="px-4 py-4">
                            <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
                              {decision.momentum_rankings.length > 0 && (
                                <div>
                                  <div className="mb-2 text-[10px] uppercase tracking-[0.14em] text-slate-400">资产类别动量排名</div>
                                  <div className="flex flex-wrap gap-2">
                                    {decision.momentum_rankings.map((ranking) => (
                                      <span
                                        key={ranking.ts_code}
                                        className={`rounded-full px-2.5 py-1 text-xs ${
                                          ranking.momentum > 0 ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                                        }`}
                                      >
                                        {ranking.name} {ranking.momentum > 0 ? "+" : ""}
                                        {(ranking.momentum * 100).toFixed(2)}%
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {decision.weight_diffs.length > 0 && (
                                <div>
                                  <div className="mb-2 text-[10px] uppercase tracking-[0.14em] text-amber-500">权重差异</div>
                                  <div className="flex flex-wrap gap-2">
                                    {decision.weight_diffs.map((diff) => (
                                      <span key={diff.ts_code} className="rounded-full bg-amber-100 px-2.5 py-1 text-xs text-amber-700">
                                        {diff.name}: 算法基线 {(diff.algo_weight * 100).toFixed(0)}% → 协同决策 {(diff.ai_weight * 100).toFixed(0)}%
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {decision.ai && (
                                <div className="grid gap-4 lg:grid-cols-2">
                                  <div className="space-y-3 rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-700">金融子 Agent · Fin-R1</div>
                                    <div className="text-sm font-medium text-emerald-900">{decision.ai.sub_agent?.summary}</div>
                                    <div className="text-xs leading-6 text-emerald-800">{decision.ai.sub_agent?.reasoning}</div>
                                    <ScoreChips title="Fin-R1 评分" scores={decision.ai.sub_agent?.scores} tone="sub" nameMap={nameMap} />
                                    <div className="text-xs text-emerald-900">建议配置：{formatWeights(decision.ai.sub_agent?.weights ?? {}, nameMap)}</div>
                                  </div>

                                  <div className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50/80 p-4">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-amber-700">主 Agent · GPT-5.4</div>
                                    <div className="text-sm font-medium text-amber-900">{decision.ai.main_agent?.summary}</div>
                                    <div className="text-xs leading-6 text-amber-800">{decision.ai.main_agent?.reasoning}</div>
                                    <ScoreChips title="GPT-5.4 评分" scores={decision.ai.main_agent?.scores} tone="main" nameMap={nameMap} />
                                    <div className="text-xs text-amber-900">最终配置：{formatWeights(decision.ai.target_weights, nameMap)}</div>
                                  </div>
                                </div>
                              )}

                              {decision.ai?.weighted_scores && (
                                <ScoreChips title="60/40 加权评分" scores={decision.ai.weighted_scores} tone="weighted" nameMap={nameMap} />
                              )}

                              {decision.algo?.reasoning && (
                                <div>
                                  <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-indigo-400">算法决策依据</div>
                                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
                                    {decision.algo.reasoning}
                                  </div>
                                </div>
                              )}

                              {decision.ai?.reasoning && (
                                <div>
                                  <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-slate-500">协同决策依据</div>
                                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-600">
                                    {decision.ai.reasoning}
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/60 bg-white/90 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="mb-3 flex items-center gap-4">
            <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">交易记录对比</h2>
            <div className="flex gap-1">
              <button
                onClick={() => setTradeTab("algo")}
                className={`rounded-full px-3 py-1 text-xs transition ${
                  tradeTab === "algo" ? "bg-indigo-100 text-indigo-700" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                算法基线 ({trades?.algo_trades.length ?? 0})
              </button>
              <button
                onClick={() => setTradeTab("ai")}
                className={`rounded-full px-3 py-1 text-xs transition ${
                  tradeTab === "ai" ? "bg-amber-100 text-amber-700" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                协同决策 ({trades?.ai_trades.length ?? 0})
              </button>
            </div>
          </div>
          <TradeTable trades={tradeTab === "algo" ? (trades?.algo_trades ?? []) : (trades?.ai_trades ?? [])} />
        </div>
      </div>
    </div>
  );
}
