"use client";

import { useEffect, useState, useCallback, Fragment } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid, Legend,
} from "recharts";
import {
  api, CompareStatus, CompareNavPoint, CompareMetrics,
  DecisionComparison, CompareTrades, Trade, Metrics,
} from "@/lib/api";

function formatDate(d: unknown) {
  const s = String(d);
  if (s.length === 8) return `${s.slice(4, 6)}-${s.slice(6)}`;
  return s;
}

function MetricPair({ label, algoVal, aiVal }: { label: string; algoVal: string; aiVal: string | null }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="text-xs text-slate-500 mb-2">{label}</div>
      <div className="flex justify-between items-end gap-4">
        <div>
          <div className="text-[10px] text-indigo-400 mb-0.5">算法</div>
          <div className="text-lg font-bold text-indigo-600">{algoVal}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-amber-400 mb-0.5">AI</div>
          <div className="text-lg font-bold text-amber-600">{aiVal ?? "—"}</div>
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
  if (!trades.length) return <div className="text-slate-400 text-sm py-4 text-center">暂无交易记录</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-500 border-b border-slate-200">
            <th className="text-left py-2 px-2">日期</th>
            <th className="text-left py-2 px-2">ETF</th>
            <th className="text-left py-2 px-2">方向</th>
            <th className="text-right py-2 px-2">股数</th>
            <th className="text-right py-2 px-2">价格</th>
            <th className="text-right py-2 px-2">金额</th>
          </tr>
        </thead>
        <tbody>
          {trades.slice(-30).reverse().map((t, i) => (
            <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-1.5 px-2 font-mono text-xs text-slate-600">{formatDate(t.date)}</td>
              <td className="py-1.5 px-2 text-slate-700">{t.name}</td>
              <td className={`py-1.5 px-2 font-medium ${t.direction === "BUY" ? "text-green-600" : "text-red-600"}`}>
                {t.direction === "BUY" ? "买入" : "卖出"}
              </td>
              <td className="py-1.5 px-2 text-right font-mono text-slate-700">{t.shares.toLocaleString()}</td>
              <td className="py-1.5 px-2 text-right font-mono text-slate-700">{t.price.toFixed(3)}</td>
              <td className="py-1.5 px-2 text-right font-mono text-slate-700">{t.amount.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
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

  const loadData = useCallback(async () => {
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
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 轮询 agent 状态
  useEffect(() => {
    if (!status || status.agent_status === "completed" || status.agent_status === "failed") return;
    const timer = setInterval(async () => {
      try {
        const s = await api.compareStatus();
        setStatus(s);
        if (s.agent_status === "completed") {
          loadData(); // agent 完成后刷新全部数据
        }
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(timer);
  }, [status, loadData]);

  const toggleRow = (date: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-slate-400 text-lg animate-pulse">加载中...</div>
      </div>
    );
  }

  const algo = metrics?.algo;
  const ai = metrics?.ai;
  const hasAi = status?.agent_status === "completed" && ai != null;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Agent 状态横幅 */}
      {status && status.agent_status !== "completed" && (
        <div className={`rounded-xl p-4 text-sm ${
          status.agent_status === "failed"
            ? "bg-red-50 border border-red-200 text-red-700"
            : "bg-amber-50 border border-amber-200 text-amber-700"
        }`}>
          {status.agent_status === "pending" && "AI 回测等待启动..."}
          {status.agent_status === "running" && "AI 回测进行中，完成后将自动刷新对比数据..."}
          {status.agent_status === "failed" && `AI 回测失败: ${status.agent_error}`}
        </div>
      )}

      {/* 指标对比卡片 */}
      {algo && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricPair label="总收益率" algoVal={fmtPct(algo.total_return)!} aiVal={fmtPct(ai?.total_return)} />
          <MetricPair label="年化收益" algoVal={fmtPct(algo.annualized_return)!} aiVal={fmtPct(ai?.annualized_return)} />
          <MetricPair label="最大回撤" algoVal={`${algo.max_drawdown}%`} aiVal={ai ? `${ai.max_drawdown}%` : null} />
          <MetricPair label="夏普比率" algoVal={`${algo.sharpe_ratio}`} aiVal={ai ? `${ai.sharpe_ratio}` : null} />
          <MetricPair label="交易次数" algoVal={`${algo.total_trades}`} aiVal={ai ? `${ai.total_trades}` : null} />
        </div>
      )}

      {/* 净值对比图 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600 mb-3">净值对比曲线</h2>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={navData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} domain={["dataMin - 10000", "dataMax + 10000"]} tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}万`} />
            <Tooltip
              contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8 }}
              labelFormatter={formatDate}
              formatter={(v: number, name: string) => [
                `${v.toLocaleString()} 元`,
                name === "algo_nav" ? "算法" : "AI",
              ]}
            />
            <Legend formatter={(v: string) => (v === "algo_nav" ? "算法策略" : "AI 策略")} />
            <Line type="monotone" dataKey="algo_nav" stroke="#6366f1" strokeWidth={2} dot={false} name="algo_nav" />
            {hasAi && <Line type="monotone" dataKey="ai_nav" stroke="#f59e0b" strokeWidth={2} dot={false} name="ai_nav" />}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 回撤对比图 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600 mb-3">回撤对比曲线</h2>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={navData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
            <Tooltip
              contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8 }}
              labelFormatter={formatDate}
              formatter={(v: number, name: string) => [
                `${(v * 100).toFixed(2)}%`,
                name === "algo_drawdown" ? "算法" : "AI",
              ]}
            />
            <Legend formatter={(v: string) => (v === "algo_drawdown" ? "算法回撤" : "AI 回撤")} />
            <Area type="monotone" dataKey="algo_drawdown" stroke="#818cf8" fill="#c7d2fe40" strokeWidth={1.5} name="algo_drawdown" />
            {hasAi && <Area type="monotone" dataKey="ai_drawdown" stroke="#fbbf24" fill="#fef3c740" strokeWidth={1.5} name="ai_drawdown" />}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 调仓决策对比表 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600 mb-3">调仓决策对比</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 border-b border-slate-200">
                <th className="text-left py-2 px-3 w-24">日期</th>
                <th className="text-left py-2 px-3">算法配置</th>
                <th className="text-left py-2 px-3">AI 配置</th>
                <th className="text-center py-2 px-3 w-16">一致</th>
                <th className="text-center py-2 px-3 w-16">操作</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d) => {
                const isExpanded = expandedRows.has(d.date);
                const rowBg = d.decisions_match ? "" : "bg-amber-50";
                const fmtWeights = (weights: Record<string, number>) =>
                  Object.entries(weights)
                    .filter(([, w]) => w > 0)
                    .sort(([, a], [, b]) => b - a)
                    .map(([code, w]) => `${code.split(".")[0]} ${(w * 100).toFixed(0)}%`)
                    .join(", ");
                return (
                  <Fragment key={d.date}>
                    <tr className={`border-b border-slate-100 hover:bg-slate-50/50 ${rowBg}`}>
                      <td className="py-2 px-3 font-mono text-xs text-slate-600">{formatDate(d.date)}</td>
                      <td className="py-2 px-3 text-xs text-slate-700">
                        {d.algo ? fmtWeights(d.algo.target_weights) : "—"}
                      </td>
                      <td className="py-2 px-3 text-xs text-slate-700">
                        {d.ai ? fmtWeights(d.ai.target_weights) : hasAi ? "—" : "等待中..."}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {d.ai == null ? (
                          <span className="text-slate-300">—</span>
                        ) : d.decisions_match ? (
                          <span className="text-green-500 text-xs">一致</span>
                        ) : (
                          <span className="text-amber-600 text-xs font-medium">不同</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <button
                          onClick={() => toggleRow(d.date)}
                          className="text-xs text-indigo-500 hover:text-indigo-700"
                        >
                          {isExpanded ? "收起" : "详情"}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className={rowBg}>
                        <td colSpan={5} className="px-4 py-3 bg-slate-50/50">
                          <div className="space-y-2">
                            {/* 动量排名 */}
                            {d.momentum_rankings.length > 0 && (
                              <div>
                                <div className="text-[10px] text-slate-400 mb-1">动量排名</div>
                                <div className="flex flex-wrap gap-2">
                                  {d.momentum_rankings.map((r) => (
                                    <span key={r.ts_code} className={`text-xs px-2 py-0.5 rounded ${r.momentum > 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                      {r.name} {r.momentum > 0 ? "+" : ""}{(r.momentum * 100).toFixed(2)}%
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {/* 权重差异 */}
                            {d.weight_diffs.length > 0 && (
                              <div>
                                <div className="text-[10px] text-amber-500 mb-1">权重差异</div>
                                <div className="flex flex-wrap gap-2">
                                  {d.weight_diffs.map((w) => (
                                    <span key={w.ts_code} className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                                      {w.name}: 算法 {(w.algo_weight * 100).toFixed(0)}% → AI {(w.ai_weight * 100).toFixed(0)}% ({w.delta > 0 ? "+" : ""}{(w.delta * 100).toFixed(1)}%)
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {/* 算法理由 */}
                            {d.algo?.reasoning && (
                              <div>
                                <div className="text-[10px] text-indigo-400 mb-1">算法决策理由</div>
                                <div className="text-xs text-slate-600 bg-white rounded p-2 border border-slate-100">{d.algo.reasoning}</div>
                              </div>
                            )}
                            {/* AI 理由 */}
                            {d.ai?.reasoning && (
                              <div>
                                <div className="text-[10px] text-amber-400 mb-1">AI 决策理由</div>
                                <div className="text-xs text-slate-600 bg-white rounded p-2 border border-amber-100 whitespace-pre-wrap">{d.ai.reasoning}</div>
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

      {/* 交易记录对比 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-4 mb-3">
          <h2 className="text-sm font-medium text-slate-600">交易记录对比</h2>
          <div className="flex gap-1">
            <button
              onClick={() => setTradeTab("algo")}
              className={`text-xs px-3 py-1 rounded-full transition ${
                tradeTab === "algo" ? "bg-indigo-100 text-indigo-700" : "text-slate-400 hover:text-slate-600"
              }`}
            >
              算法 ({trades?.algo_trades.length ?? 0})
            </button>
            <button
              onClick={() => setTradeTab("ai")}
              className={`text-xs px-3 py-1 rounded-full transition ${
                tradeTab === "ai" ? "bg-amber-100 text-amber-700" : "text-slate-400 hover:text-slate-600"
              }`}
            >
              AI ({trades?.ai_trades.length ?? 0})
            </button>
          </div>
        </div>
        <TradeTable trades={tradeTab === "algo" ? (trades?.algo_trades ?? []) : (trades?.ai_trades ?? [])} />
      </div>
    </div>
  );
}
