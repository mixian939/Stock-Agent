"""绩效追踪与指标计算"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from stock_agent.engine.portfolio import Portfolio


class PerformanceTracker:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.nav_history: list[dict] = []
        self.peak_nav: float = initial_capital

    def record(self, date: str, portfolio: Portfolio, prices: dict[str, float]):
        nav = portfolio.get_total_value(prices)
        if nav > self.peak_nav:
            self.peak_nav = nav
        drawdown = (nav / self.peak_nav - 1) if self.peak_nav > 0 else 0

        self.nav_history.append({
            "date": date,
            "nav": round(nav, 2),
            "cash": round(portfolio.cash, 2),
            "positions_value": round(nav - portfolio.cash, 2),
            "drawdown": round(drawdown, 4),
        })

    def get_metrics(self) -> dict:
        if len(self.nav_history) < 2:
            return {"error": "数据不足"}

        navs = [r["nav"] for r in self.nav_history]
        first, last = navs[0], navs[-1]
        n_days = len(navs)

        total_return = last / first - 1
        ann_factor = 252 / n_days if n_days > 0 else 1
        ann_return = (1 + total_return) ** ann_factor - 1

        # 日收益率序列
        daily_returns = np.diff(navs) / navs[:-1]
        volatility = float(np.std(daily_returns)) * math.sqrt(252)
        risk_free = 0.025  # 年化无风险利率
        sharpe = (ann_return - risk_free) / volatility if volatility > 0 else 0

        # 最大回撤
        drawdowns = [r["drawdown"] for r in self.nav_history]
        max_dd = min(drawdowns)
        max_dd_idx = drawdowns.index(max_dd)
        max_dd_date = self.nav_history[max_dd_idx]["date"]

        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

        return {
            "initial_capital": self.initial_capital,
            "final_value": round(last, 2),
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(ann_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "max_drawdown_date": max_dd_date,
            "sharpe_ratio": round(sharpe, 2),
            "calmar_ratio": round(calmar, 2),
            "trading_days": n_days,
            "total_trades": 0,  # 由外部填入
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.nav_history)
