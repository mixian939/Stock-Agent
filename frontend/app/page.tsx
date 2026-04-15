"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, CartesianGrid,
} from "recharts";
import { api, NavPoint, PositionsData, Trade, Metrics, DrawdownPoint } from "@/lib/api";

const COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6", "#ec4899"];

function formatDate(d: unknown) {
  const s = String(d);
  if (s.length === 8) return `${s.slice(4, 6)}-${s.slice(6)}`;
  return s;
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-slate-800">{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [nav, setNav] = useState<NavPoint[]>([]);
  const [positions, setPositions] = useState<PositionsData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [drawdown, setDrawdown] = useState<DrawdownPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.navHistory(),
      api.positions(),
      api.trades(),
      api.metrics(),
      api.drawdown(),
    ]).then(([n, p, t, m, d]) => {
      setNav(n);
      setPositions(p);
      setTrades(t);
      setMetrics(m);
      setDrawdown(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-slate-400 text-lg animate-pulse">加载中...</div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-red-600">无法加载数据，请确认后端已启动 (localhost:7777)</div>
      </div>
    );
  }

  const returnColor = metrics.total_return >= 0 ? "text-green-600" : "text-red-600";

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* 绩效指标卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard label="总收益率" value={`${metrics.total_return >= 0 ? "+" : ""}${metrics.total_return}%`} />
        <MetricCard label="年化收益" value={`${metrics.annualized_return >= 0 ? "+" : ""}${metrics.annualized_return}%`} />
        <MetricCard label="最大回撤" value={`${metrics.max_drawdown}%`} sub={formatDate(metrics.max_drawdown_date)} />
        <MetricCard label="夏普比率" value={`${metrics.sharpe_ratio}`} />
        <MetricCard label="卡尔玛比率" value={`${metrics.calmar_ratio}`} />
        <MetricCard label="总交易次数" value={`${metrics.total_trades}`} sub={`${metrics.trading_days} 交易日`} />
      </div>

      {/* 资产总览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-500">初始资金</div>
          <div className="text-lg font-mono text-slate-800">{metrics.initial_capital.toLocaleString()} 元</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-500">最终资产</div>
          <div className={`text-lg font-mono ${returnColor}`}>{metrics.final_value.toLocaleString()} 元</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-500">波动率</div>
          <div className="text-lg font-mono text-slate-800">{metrics.volatility}%</div>
        </div>
      </div>

      {/* 净值曲线 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600 mb-3">净值曲线</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={nav}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} domain={["dataMin - 10000", "dataMax + 10000"]} tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}万`} />
            <Tooltip
              contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 8 }}
              labelFormatter={formatDate}
              formatter={(v) => [`${Number(v).toLocaleString()} 元`, "净值"]}
            />
            <Line type="monotone" dataKey="nav" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 回撤曲线 */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-600 mb-3">回撤曲线</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={drawdown}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Tooltip
                contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 8 }}
                labelFormatter={formatDate}
                formatter={(v) => [`${(Number(v) * 100).toFixed(2)}%`, "回撤"]}
              />
              <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="#fecaca40" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* 持仓饼图 */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-600 mb-3">最终持仓分布</h2>
          {positions && positions.positions.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={[
                    ...positions.positions.map((p) => ({ name: p.name, value: p.value })),
                    ...(positions.cash > 1 ? [{ name: "现金", value: positions.cash }] : []),
                  ]}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
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
                  contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 8 }}
                  formatter={(v) => [`${Number(v).toLocaleString()} 元`]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-slate-400">空仓</div>
          )}
        </div>
      </div>

      {/* 交易记录表格 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600 mb-3">交易记录 (最近 30 笔)</h2>
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
                <th className="text-right py-2 px-2">佣金</th>
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
                  <td className="py-1.5 px-2 text-right font-mono text-slate-400">{t.commission.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
