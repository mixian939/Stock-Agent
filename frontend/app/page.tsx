"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
} from "recharts";
import {
  api,
  NavPoint,
  PositionsData,
  Trade,
  Metrics,
  DrawdownPoint,
  CompareStatus,
  DecisionComparison,
} from "@/lib/api";

const COLORS = ["#14532d", "#0f766e", "#b45309", "#be123c", "#1d4ed8", "#7c3aed", "#0f172a"];

function formatDate(d: unknown) {
  const s = String(d);
  if (s.length === 8) return `${s.slice(4, 6)}-${s.slice(6)}`;
  return s;
}

function formatWeights(weights: Record<string, number>) {
  return Object.entries(weights)
    .filter(([, w]) => w > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([code, w]) => `${code.split(".")[0]} ${(w * 100).toFixed(0)}%`)
    .join(" · ");
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-3xl border border-white/50 bg-white/85 p-4 shadow-[0_12px_35px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function ScoreBar({ label, value, tone }: { label: string; value: number; tone: "sub" | "main" | "weighted" }) {
  const palette =
    tone === "sub"
      ? "from-emerald-500 to-teal-400"
      : tone === "main"
        ? "from-amber-500 to-orange-400"
        : "from-slate-700 to-slate-500";
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-medium text-slate-800">{value.toFixed(1)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full bg-gradient-to-r ${palette}`} style={{ width: `${Math.max(4, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [nav, setNav] = useState<NavPoint[]>([]);
  const [positions, setPositions] = useState<PositionsData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [drawdown, setDrawdown] = useState<DrawdownPoint[]>([]);
  const [compareStatus, setCompareStatus] = useState<CompareStatus | null>(null);
  const [compareDecisions, setCompareDecisions] = useState<DecisionComparison[]>([]);
  const [dataSources, setDataSources] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.navHistory(),
      api.positions(),
      api.trades(),
      api.metrics(),
      api.drawdown(),
      api.compareStatus(),
      api.compareDecisions(),
      api.dataSources(),
    ])
      .then(([n, p, t, m, d, status, decisions, sources]) => {
        setNav(n);
        setPositions(p);
        setTrades(t);
        setMetrics(m);
        setDrawdown(d);
        setCompareStatus(status);
        setCompareDecisions(decisions);
        setDataSources(sources);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-lg text-slate-400 animate-pulse">加载中...</div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-red-600">无法加载数据，请确认后端已启动 (localhost:7777)</div>
      </div>
    );
  }

  const latestAiDecision = [...compareDecisions].reverse().find((item) => item.ai);
  const latestWeightedScores = latestAiDecision?.ai?.weighted_scores
    ? Object.entries(latestAiDecision.ai.weighted_scores).sort(([, a], [, b]) => b - a).slice(0, 3)
    : [];
  const returnColor = metrics.total_return >= 0 ? "text-emerald-700" : "text-rose-700";
  const aiReady = compareStatus?.agent_status === "completed" && latestAiDecision?.ai;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(20,83,45,0.12),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)]">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
        <section className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="overflow-hidden rounded-[32px] border border-emerald-100/70 bg-[linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(20,83,45,0.92)_55%,_rgba(13,148,136,0.82))] p-6 text-white shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-200/80">Stock Agent Dashboard</div>
            <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight md:text-4xl">
              ETF 池已扩展为多候选标的，但交易仍然只围绕 7 个资产类别轮动。
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-emerald-50/90">
              首页继续展示算法基线回测，同时补充双 Agent 决策摘要。AI 模式下由本地 LM Studio 金融子 Agent 先提建议，再由主 Agent 以 60/40 评分权重做最终裁决。
            </p>
            <div className="mt-6 flex flex-wrap gap-3 text-xs text-white/85">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">主 Agent: {compareStatus?.agent_status === "completed" ? "已完成回测" : compareStatus?.agent_status ?? "未知"}</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">子 Agent 权重 60%</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">主 Agent 权重 40%</span>
            </div>
          </div>

          <div className="rounded-[32px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.1)] backdrop-blur">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Data Sources</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">数据接口摘要</div>
              </div>
              <div className="rounded-full bg-slate-900 px-3 py-1 text-xs text-white">
                {Object.keys(dataSources).length} 只 ETF
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(dataSources).length > 0 ? (
                Object.entries(dataSources).map(([code, source]) => (
                  <span key={code} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700">
                    {code} · {source}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-400">当前尚未记录数据源元信息</span>
              )}
            </div>
          </div>
        </section>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <MetricCard label="总收益率" value={`${metrics.total_return >= 0 ? "+" : ""}${metrics.total_return}%`} />
          <MetricCard label="年化收益" value={`${metrics.annualized_return >= 0 ? "+" : ""}${metrics.annualized_return}%`} />
          <MetricCard label="最大回撤" value={`${metrics.max_drawdown}%`} sub={formatDate(metrics.max_drawdown_date)} />
          <MetricCard label="夏普比率" value={`${metrics.sharpe_ratio}`} />
          <MetricCard label="卡尔玛比率" value={`${metrics.calmar_ratio}`} />
          <MetricCard label="总交易次数" value={`${metrics.total_trades}`} sub={`${metrics.trading_days} 交易日`} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="flex items-end justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Headless Baseline</div>
                <div className={`mt-2 text-3xl font-semibold ${returnColor}`}>{metrics.final_value.toLocaleString()} 元</div>
              </div>
              <div className="text-right text-sm text-slate-500">
                <div>初始资金 {metrics.initial_capital.toLocaleString()} 元</div>
                <div>波动率 {metrics.volatility}%</div>
              </div>
            </div>
            <div className="mt-4 h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={nav}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4f0" />
                  <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} domain={["dataMin - 10000", "dataMax + 10000"]} tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}万`} />
                  <Tooltip
                    contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16 }}
                    labelFormatter={formatDate}
                    formatter={(v) => [`${Number(v).toLocaleString()} 元`, "净值"]}
                  />
                  <Line type="monotone" dataKey="nav" stroke="#0f766e" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-200/80 bg-[linear-gradient(160deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Dual Agent</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">最新协同裁决</div>
              </div>
              <div className={`rounded-full px-3 py-1 text-xs ${
                aiReady ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
              }`}>
                {aiReady ? "已就绪" : compareStatus?.agent_status === "failed" ? "失败" : "处理中"}
              </div>
            </div>

            {latestAiDecision?.ai ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-2xl bg-slate-950 p-4 text-white">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Final Target</div>
                  <div className="mt-2 text-lg font-semibold">{formatWeights(latestAiDecision.ai.target_weights)}</div>
                  <div className="mt-2 text-xs text-slate-300">
                    日期 {formatDate(latestAiDecision.date)} · 执行状态 {latestAiDecision.ai.execution_status ?? "unknown"} ·
                    {latestAiDecision.ai.should_rebalance ? " 调仓" : " 持有不动"}
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  {latestWeightedScores.map(([code, score]) => (
                    <div key={code} className="rounded-2xl border border-slate-200 bg-white p-3">
                      <div className="text-xs text-slate-500">{code}</div>
                      <div className="mt-1 font-medium text-slate-900">{score.toFixed(1)}</div>
                      <div className="mt-2 space-y-2">
                        <ScoreBar label="加权分" value={score} tone="weighted" />
                        <ScoreBar label="子 Agent" value={latestAiDecision.ai?.sub_agent?.scores?.[code] ?? 0} tone="sub" />
                        <ScoreBar label="主 Agent" value={latestAiDecision.ai?.main_agent?.scores?.[code] ?? 0} tone="main" />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                    <div className="text-xs uppercase tracking-[0.16em] text-emerald-700">金融子 Agent</div>
                    <div className="mt-2 text-sm font-medium text-emerald-900">{latestAiDecision.ai.sub_agent?.summary}</div>
                    <div className="mt-2 text-xs leading-6 text-emerald-800">
                      {latestAiDecision.ai.sub_agent?.reasoning}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4">
                    <div className="text-xs uppercase tracking-[0.16em] text-amber-700">主 Agent</div>
                    <div className="mt-2 text-sm font-medium text-amber-900">{latestAiDecision.ai.main_agent?.summary}</div>
                    <div className="mt-2 text-xs leading-6 text-amber-800">
                      {latestAiDecision.ai.main_agent?.reasoning}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                AI 回测尚未产出最新双 Agent 决策。完成后这里会展示子 Agent 建议、主 Agent 裁决和加权分。
              </div>
            )}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
            <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">Drawdown Curve</h2>
            <div className="mt-4 h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={drawdown}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                  <Tooltip
                    contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16 }}
                    labelFormatter={formatDate}
                    formatter={(v) => [`${(Number(v) * 100).toFixed(2)}%`, "回撤"]}
                  />
                  <Area type="monotone" dataKey="drawdown" stroke="#be123c" fill="#fecdd355" strokeWidth={1.8} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
            <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">Final Allocation</h2>
            {positions && positions.positions.length > 0 ? (
              <div className="mt-4 h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        ...positions.positions.map((p) => ({ name: p.name, value: p.value })),
                        ...(positions.cash > 1 ? [{ name: "现金", value: positions.cash }] : []),
                      ]}
                      cx="50%"
                      cy="50%"
                      outerRadius={84}
                      label={(props) => `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`}
                      labelLine={{ stroke: "#94a3b8" }}
                      dataKey="value"
                    >
                      {positions.positions.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                      {positions.cash > 1 && <Cell fill="#cbd5e1" />}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16 }}
                      formatter={(v) => [`${Number(v).toLocaleString()} 元`]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="mt-6 flex h-[220px] items-center justify-center text-slate-400">空仓</div>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">Recent Trades</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="px-2 py-2 text-left">日期</th>
                  <th className="px-2 py-2 text-left">ETF</th>
                  <th className="px-2 py-2 text-left">方向</th>
                  <th className="px-2 py-2 text-right">股数</th>
                  <th className="px-2 py-2 text-right">价格</th>
                  <th className="px-2 py-2 text-right">金额</th>
                  <th className="px-2 py-2 text-right">佣金</th>
                </tr>
              </thead>
              <tbody>
                {trades.slice(-30).reverse().map((trade, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50/80">
                    <td className="px-2 py-1.5 font-mono text-xs text-slate-600">{formatDate(trade.date)}</td>
                    <td className="px-2 py-1.5 text-slate-700">{trade.name}</td>
                    <td className={`px-2 py-1.5 font-medium ${trade.direction === "BUY" ? "text-emerald-600" : "text-rose-600"}`}>
                      {trade.direction === "BUY" ? "买入" : "卖出"}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.shares.toLocaleString()}</td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.price.toFixed(3)}</td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-700">{trade.amount.toLocaleString()}</td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-400">{trade.commission.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
