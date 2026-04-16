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

function formatWeights(weights: Record<string, number>, nameMap?: Record<string, string>) {
  return Object.entries(weights)
    .filter(([, w]) => w > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([code, w]) => `${nameMap?.[code] ?? code.split(".")[0]} ${(w * 100).toFixed(0)}%`)
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
  const [btStart, setBtStart] = useState("2025-01-01");
  const [btEnd, setBtEnd] = useState("2025-06-30");
  const [backtesting, setBacktesting] = useState(false);
  const [btStatus, setBtStatus] = useState("");

  const loadData = () => {
    setLoading(true);
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
  };

  useEffect(() => { loadData(); }, []);

  async function handleRunBacktest() {
    if (backtesting) return;
    setBacktesting(true);
    setBtStatus("正在提交回测请求...");
    try {
      const start = btStart.replace(/-/g, "");
      const end = btEnd.replace(/-/g, "");
      await api.runBacktest(start, end);
      setBtStatus("Headless 回测运行中...");
      // 轮询直到完成
      const poll = async () => {
        while (true) {
          await new Promise((r) => setTimeout(r, 3000));
          try {
            const h = await api.health();
            if (h.backtest_ready && h.agent_status === "completed") {
              setBtStatus("回测完成，正在刷新数据...");
              break;
            } else if (h.agent_status === "failed") {
              setBtStatus("Agent 回测异常，Headless 数据已刷新");
              break;
            } else if (h.backtest_ready && h.agent_status === "running") {
              setBtStatus("Agent 回测运行中...");
            }
          } catch {
            // 服务可能在重启，继续轮询
          }
        }
      };
      await poll();
      loadData();
    } catch (e: unknown) {
      setBtStatus(e instanceof Error ? e.message : "回测请求失败");
    } finally {
      setBacktesting(false);
      setTimeout(() => setBtStatus(""), 5000);
    }
  }

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
        <div className="text-red-600">数据加载失败，请确认后端服务已启动</div>
      </div>
    );
  }

  const latestAiDecision = [...compareDecisions].reverse().find((item) => item.ai);
  const latestWeightedScores = latestAiDecision?.ai?.weighted_scores
    ? Object.entries(latestAiDecision.ai.weighted_scores).sort(([, a], [, b]) => b - a).slice(0, 3)
    : [];
  const returnColor = metrics.total_return >= 0 ? "text-emerald-700" : "text-rose-700";
  const aiReady = compareStatus?.agent_status === "completed" && latestAiDecision?.ai;

  const nameMap: Record<string, string> = {};
  for (const d of compareDecisions) {
    for (const r of d.momentum_rankings) nameMap[r.ts_code] = r.name;
  }
  if (positions) {
    for (const p of positions.positions) nameMap[p.ts_code] = p.name;
  }
  for (const t of trades) nameMap[t.ts_code] = t.name;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(20,83,45,0.12),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)]">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
        <section className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="overflow-hidden rounded-[32px] border border-emerald-100/70 bg-[linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(20,83,45,0.92)_55%,_rgba(13,148,136,0.82))] p-6 text-white shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-200/80">System Overview</div>
            <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight md:text-4xl">
              ETF 动量轮动 + 双 Agent 协同调仓系统
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-emerald-50/90">
              基于动量因子从 ETF 候选池中筛选标的，通过双 Agent 协同完成调仓决策。金融子 Agent（Fin-R1）负责市场分析与仓位建议，主 Agent（GPT-5.4）综合评分后做最终裁决，评分权重为子 Agent 60% / 主 Agent 40%。
            </p>
            <div className="mt-6 flex flex-wrap gap-3 text-xs text-white/85">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">子 Agent: Fin-R1（权重 60%）</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">主 Agent: GPT-5.4（权重 40%）</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">状态: {compareStatus?.agent_status === "completed" ? "回测完成" : compareStatus?.agent_status ?? "未知"}</span>
            </div>
          </div>

          <div className="rounded-[32px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.1)] backdrop-blur">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Data Sources</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">ETF 候选池</div>
              </div>
              <div className="rounded-full bg-slate-900 px-3 py-1 text-xs text-white">
                {Object.keys(dataSources).length} 只标的
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
                <span className="text-sm text-slate-400">暂无数据源信息</span>
              )}
            </div>
          </div>
        </section>

        <div className="rounded-[28px] border border-white/60 bg-white/88 p-4 shadow-[0_12px_35px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Backtest Range</div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-600">开始日期</label>
              <input
                type="date"
                value={btStart}
                onChange={(e) => setBtStart(e.target.value)}
                disabled={backtesting}
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 outline-none transition focus:border-emerald-500 disabled:opacity-50"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-600">结束日期</label>
              <input
                type="date"
                value={btEnd}
                onChange={(e) => setBtEnd(e.target.value)}
                disabled={backtesting}
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 outline-none transition focus:border-emerald-500 disabled:opacity-50"
              />
            </div>
            <button
              onClick={handleRunBacktest}
              disabled={backtesting}
              className="rounded-xl bg-emerald-700 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {backtesting ? "回测中..." : "开始回测"}
            </button>
            {btStatus && (
              <span className="text-xs text-slate-500 animate-pulse">{btStatus}</span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <MetricCard label="总收益率" value={`${metrics.total_return >= 0 ? "+" : ""}${metrics.total_return}%`} />
          <MetricCard label="年化收益" value={`${metrics.annualized_return >= 0 ? "+" : ""}${metrics.annualized_return}%`} />
          <MetricCard label="最大回撤" value={`${metrics.max_drawdown}%`} sub={formatDate(metrics.max_drawdown_date)} />
          <MetricCard label="夏普比率" value={`${metrics.sharpe_ratio}`} />
          <MetricCard label="卡尔玛比率" value={`${metrics.calmar_ratio}`} />
          <MetricCard label="总交易次数" value={`${metrics.total_trades}`} sub={`${metrics.trading_days} 交易日`} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="flex items-end justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Baseline</div>
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
                <div className="mt-1 text-xl font-semibold text-slate-900">最新协同决策</div>
              </div>
              <div className={`rounded-full px-3 py-1 text-xs ${
                aiReady ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
              }`}>
                {aiReady ? "已完成" : compareStatus?.agent_status === "failed" ? "异常" : "运行中"}
              </div>
            </div>

            {latestAiDecision?.ai ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-2xl bg-slate-950 p-4 text-white">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Target Weights</div>
                  <div className="mt-2 text-lg font-semibold">{formatWeights(latestAiDecision.ai.target_weights, nameMap)}</div>
                  <div className="mt-2 text-xs text-slate-300">
                    {formatDate(latestAiDecision.date)} · {latestAiDecision.ai.execution_status ?? "未知"} ·
                    {latestAiDecision.ai.should_rebalance ? " 执行调仓" : " 维持持仓"}
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  {latestWeightedScores.map(([code, score]) => (
                    <div key={code} className="rounded-2xl border border-slate-200 bg-white p-3">
                      <div className="text-xs text-slate-500">{nameMap[code] ?? code}</div>
                      <div className="mt-1 font-medium text-slate-900">{score.toFixed(1)}</div>
                      <div className="mt-2 space-y-2">
                        <ScoreBar label="综合评分" value={score} tone="weighted" />
                        <ScoreBar label="Fin-R1" value={latestAiDecision.ai?.sub_agent?.scores?.[code] ?? 0} tone="sub" />
                        <ScoreBar label="GPT-5.4" value={latestAiDecision.ai?.main_agent?.scores?.[code] ?? 0} tone="main" />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                    <div className="text-xs uppercase tracking-[0.16em] text-emerald-700">金融子 Agent · Fin-R1</div>
                    <div className="mt-2 text-sm font-medium text-emerald-900">{latestAiDecision.ai.sub_agent?.summary}</div>
                    <div className="mt-2 text-xs leading-6 text-emerald-800">
                      {latestAiDecision.ai.sub_agent?.reasoning}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4">
                    <div className="text-xs uppercase tracking-[0.16em] text-amber-700">主 Agent · GPT-5.4</div>
                    <div className="mt-2 text-sm font-medium text-amber-900">{latestAiDecision.ai.main_agent?.summary}</div>
                    <div className="mt-2 text-xs leading-6 text-amber-800">
                      {latestAiDecision.ai.main_agent?.reasoning}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                双 Agent 回测尚未完成，完成后将展示 Fin-R1 与 GPT-5.4 的协同决策结果及综合评分。
              </div>
            )}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
            <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">回撤曲线</h2>
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
            <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">期末持仓分布</h2>
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
              <div className="mt-6 flex h-[220px] items-center justify-center text-slate-400">当前空仓</div>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">近期交易记录</h2>
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
