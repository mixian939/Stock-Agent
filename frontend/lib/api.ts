const BASE = "/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface NavPoint {
  date: string;
  nav: number;
  cash: number;
  positions_value: number;
  drawdown: number;
}

export interface Position {
  ts_code: string;
  name: string;
  shares: number;
  price: number;
  value: number;
  weight: number;
}

export interface PositionsData {
  total_value: number;
  cash: number;
  positions: Position[];
}

export interface Trade {
  run_id: string;
  date: string;
  ts_code: string;
  name: string;
  direction: "BUY" | "SELL";
  shares: number;
  price: number;
  amount: number;
  commission: number;
}

export interface Metrics {
  initial_capital: number;
  final_value: number;
  total_return: number;
  annualized_return: number;
  volatility: number;
  max_drawdown: number;
  max_drawdown_date: string;
  sharpe_ratio: number;
  calmar_ratio: number;
  trading_days: number;
  total_trades: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

// --- 对比相关接口 ---

export interface CompareStatus {
  headless_ready: boolean;
  agent_status: "pending" | "running" | "completed" | "failed";
  agent_error: string | null;
}

export interface CompareNavPoint {
  date: string;
  algo_nav: number;
  algo_drawdown: number;
  ai_nav?: number;
  ai_drawdown?: number;
}

export interface CompareMetrics {
  algo: Metrics;
  ai: Metrics | null;
}

export interface WeightDiff {
  ts_code: string;
  name: string;
  algo_weight: number;
  ai_weight: number;
  delta: number;
}

export interface DecisionSide {
  target_weights: Record<string, number>;
  reasoning: string;
}

export interface MomentumRanking {
  ts_code: string;
  name: string;
  momentum: number;
}

export interface DecisionComparison {
  date: string;
  algo: DecisionSide | null;
  ai: DecisionSide | null;
  momentum_rankings: MomentumRanking[];
  decisions_match: boolean;
  weight_diffs: WeightDiff[];
}

export interface CompareTrades {
  algo_trades: Trade[];
  ai_trades: Trade[];
}

export const api = {
  navHistory: () => fetchJSON<NavPoint[]>("/dashboard/nav-history"),
  positions: () => fetchJSON<PositionsData>("/dashboard/current-positions"),
  trades: () => fetchJSON<Trade[]>("/dashboard/trade-history"),
  metrics: () => fetchJSON<Metrics>("/dashboard/performance-metrics"),
  drawdown: () => fetchJSON<DrawdownPoint[]>("/dashboard/drawdown-curve"),
  chat: async (message: string): Promise<string> => {
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`Chat error: ${res.status}`);
    const data = await res.json();
    return data.reply;
  },

  // --- 对比 API ---
  compareStatus: () => fetchJSON<CompareStatus>("/compare/status"),
  compareNav: () => fetchJSON<CompareNavPoint[]>("/compare/nav"),
  compareMetrics: () => fetchJSON<CompareMetrics>("/compare/metrics"),
  compareDecisions: () => fetchJSON<DecisionComparison[]>("/compare/decisions"),
  compareTrades: () => fetchJSON<CompareTrades>("/compare/trades"),
};
