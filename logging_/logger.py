"""结构化日志系统：交易日志、决策日志、每日净值"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from stock_agent.config import LOG_DIR, ETF_POOL
from stock_agent.engine.portfolio import Order


class TradingLogger:
    def __init__(self, log_dir: Path = LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex[:8]
        self.trade_log: list[dict] = []
        self.decision_log: list[dict] = []
        self.daily_log: list[dict] = []

    def log_trade(self, order: Order):
        self.trade_log.append(
            {
                "run_id": self.run_id,
                "date": order.date,
                "ts_code": order.ts_code,
                "name": ETF_POOL.get(order.ts_code, ""),
                "direction": order.direction,
                "shares": order.shares,
                "price": order.price,
                "amount": round(order.amount, 2),
                "commission": round(order.commission, 2),
            }
        )

    def log_decision(
        self,
        date: str,
        momentum_rankings: list[tuple[str, float]],
        target_weights: dict[str, float],
        reasoning: str = "",
        extra: dict | None = None,
    ):
        record = {
            "run_id": self.run_id,
            "date": date,
            "momentum_rankings": [
                {"ts_code": code, "name": ETF_POOL.get(code, ""), "momentum": round(momentum, 4)}
                for code, momentum in momentum_rankings
            ],
            "target_weights": {code: round(weight, 4) for code, weight in target_weights.items()},
            "reasoning": reasoning,
        }
        if extra:
            record.update(extra)
        self.decision_log.append(record)

    def log_daily(
        self,
        date: str,
        nav: float,
        cash: float,
        positions: dict[str, int],
        drawdown: float,
    ):
        self.daily_log.append(
            {
                "run_id": self.run_id,
                "date": date,
                "nav": round(nav, 2),
                "cash": round(cash, 2),
                "positions": dict(positions),
                "drawdown": round(drawdown, 4),
            }
        )

    def log_emergency(self, date: str, orders: list[Order], drawdown: float):
        self.decision_log.append(
            {
                "run_id": self.run_id,
                "date": date,
                "type": "EMERGENCY_LIQUIDATION",
                "drawdown": round(drawdown, 4),
                "orders": [
                    {"ts_code": order.ts_code, "shares": order.shares, "price": order.price}
                    for order in orders
                ],
            }
        )

    def save_all(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_json(self.trade_log, f"trades_{ts}_{self.run_id}.json")
        self._save_json(self.decision_log, f"decisions_{ts}_{self.run_id}.json")
        self._save_json(self.daily_log, f"daily_{ts}_{self.run_id}.json")
        print(f"[Logger] 日志已保存到 {self.log_dir}")

    def _save_json(self, data: list[dict], filename: str):
        path = self.log_dir / filename
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, default=str)

    def get_trade_summary(self) -> str:
        if not self.trade_log:
            return "暂无交易记录"

        lines = ["日期 | ETF | 方向 | 股数 | 价格 | 金额"]
        lines.append("-" * 50)
        for trade in self.trade_log[-20:]:
            lines.append(
                f"{trade['date']} | {trade['name']} | {trade['direction']} | "
                f"{trade['shares']} | {trade['price']:.3f} | {trade['amount']:.2f}"
            )
        return "\n".join(lines)
