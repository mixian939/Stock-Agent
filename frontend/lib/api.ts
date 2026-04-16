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

export interface DashboardDecision {
  date: string;
  target_weights: Record<string, number>;
  reasoning: string;
  decision_mode?: string;
  execution_status?: string;
  should_rebalance?: boolean;
  score_weights?: {
    sub_agent: number;
    main_agent: number;
  };
  weighted_scores?: Record<string, number>;
}

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

export interface AgentAdvice {
  agent_name: string;
  model_id: string;
  source: string;
  should_rebalance: boolean;
  weights: Record<string, number>;
  scores: Record<string, number>;
  summary: string;
  reasoning: string;
  raw_content?: string;
}

export interface AiDecisionSide extends DecisionSide {
  decision_mode?: string;
  execution_status?: string;
  should_rebalance?: boolean;
  algorithm_recommended_weights?: Record<string, number>;
  current_weights_before?: Record<string, number>;
  score_weights?: {
    sub_agent: number;
    main_agent: number;
  };
  sub_agent?: AgentAdvice | null;
  main_agent?: AgentAdvice | null;
  weighted_scores?: Record<string, number>;
}

export interface MomentumRanking {
  ts_code: string;
  name: string;
  momentum: number;
}

export interface DecisionComparison {
  date: string;
  algo: DecisionSide | null;
  ai: AiDecisionSide | null;
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
  decisionHistory: () => fetchJSON<DashboardDecision[]>("/dashboard/decision-history"),
  dataSources: () => fetchJSON<Record<string, string>>("/dashboard/data-sources"),
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

  compareStatus: () => fetchJSON<CompareStatus>("/compare/status"),
  compareNav: () => fetchJSON<CompareNavPoint[]>("/compare/nav"),
  compareMetrics: () => fetchJSON<CompareMetrics>("/compare/metrics"),
  compareDecisions: () => fetchJSON<DecisionComparison[]>("/compare/decisions"),
  compareTrades: () => fetchJSON<CompareTrades>("/compare/trades"),

  runBacktest: async (backtest_start: string, data_end: string): Promise<void> => {
    const res = await fetch(`${BASE}/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backtest_start, data_end }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Backtest error: ${res.status}`);
    }
  },

  health: () => fetchJSON<{ status: string; backtest_ready: boolean; agent_status: string }>("/health"),
};
