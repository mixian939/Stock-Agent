"""持仓管理与订单执行"""

from __future__ import annotations

from dataclasses import dataclass, field

from stock_agent.config import COMMISSION_RATE, LOT_SIZE, INITIAL_CAPITAL


@dataclass
class Order:
    date: str
    ts_code: str
    direction: str  # "BUY" / "SELL"
    shares: int
    price: float
    amount: float
    commission: float


class Portfolio:
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.cash: float = initial_capital
        self.initial_capital = initial_capital
        self.positions: dict[str, int] = {}       # {ts_code: shares}
        self.cost_basis: dict[str, float] = {}    # {ts_code: 平均成本}
        self.order_history: list[Order] = []
        self.peak_value: float = initial_capital

    def get_total_value(self, prices: dict[str, float]) -> float:
        value = self.cash
        for code, shares in self.positions.items():
            p = prices.get(code, 0)
            value += shares * p
        return value

    def get_current_weights(self, prices: dict[str, float]) -> dict[str, float]:
        total = self.get_total_value(prices)
        if total <= 0:
            return {}
        weights = {}
        for code, shares in self.positions.items():
            p = prices.get(code, 0)
            w = (shares * p) / total
            if w > 0:
                weights[code] = round(w, 4)
        return weights

    def rebalance_to(
        self,
        target_weights: dict[str, float],
        prices: dict[str, float],
        date: str,
    ) -> list[Order]:
        """调仓到目标权重，先卖后买"""
        total_value = self.get_total_value(prices)
        orders: list[Order] = []

        # 计算目标持仓股数
        target_shares: dict[str, int] = {}
        for code, weight in target_weights.items():
            price = prices.get(code)
            if price and price > 0:
                raw_shares = (total_value * weight) / price
                target_shares[code] = int(raw_shares // LOT_SIZE) * LOT_SIZE

        # 1) 卖出：当前持仓中不在目标中 或 需要减仓的
        for code, current_shares in list(self.positions.items()):
            target = target_shares.get(code, 0)
            delta = current_shares - target
            if delta > 0:
                order = self._sell(code, delta, prices.get(code, 0), date)
                if order:
                    orders.append(order)

        # 2) 买入：目标中需要增仓的
        for code, target in target_shares.items():
            current = self.positions.get(code, 0)
            delta = target - current
            if delta > 0:
                order = self._buy(code, delta, prices.get(code, 0), date)
                if order:
                    orders.append(order)

        return orders

    def _buy(self, ts_code: str, shares: int, price: float, date: str) -> Order | None:
        if shares <= 0 or price <= 0:
            return None
        amount = shares * price
        commission = amount * COMMISSION_RATE
        total_cost = amount + commission

        if total_cost > self.cash:
            # 调整为可负担的最大手数
            affordable = int((self.cash / (price * (1 + COMMISSION_RATE))) // LOT_SIZE) * LOT_SIZE
            if affordable <= 0:
                return None
            shares = affordable
            amount = shares * price
            commission = amount * COMMISSION_RATE
            total_cost = amount + commission

        self.cash -= total_cost

        # 更新持仓和成本
        old_shares = self.positions.get(ts_code, 0)
        old_cost = self.cost_basis.get(ts_code, 0)
        new_shares = old_shares + shares
        if new_shares > 0:
            self.cost_basis[ts_code] = (old_cost * old_shares + amount) / new_shares
        self.positions[ts_code] = new_shares

        order = Order(date, ts_code, "BUY", shares, price, amount, commission)
        self.order_history.append(order)
        return order

    def _sell(self, ts_code: str, shares: int, price: float, date: str) -> Order | None:
        if shares <= 0 or price <= 0:
            return None
        current = self.positions.get(ts_code, 0)
        shares = min(shares, current)
        if shares <= 0:
            return None

        amount = shares * price
        commission = amount * COMMISSION_RATE
        self.cash += amount - commission

        new_shares = current - shares
        if new_shares <= 0:
            self.positions.pop(ts_code, None)
            self.cost_basis.pop(ts_code, None)
        else:
            self.positions[ts_code] = new_shares

        order = Order(date, ts_code, "SELL", shares, price, amount, commission)
        self.order_history.append(order)
        return order

    def check_drawdown(self, prices: dict[str, float]) -> float:
        """计算当前回撤比例（负数）"""
        current = self.get_total_value(prices)
        if current > self.peak_value:
            self.peak_value = current
        if self.peak_value <= 0:
            return 0.0
        return (current / self.peak_value) - 1

    def reset_peak(self, prices: dict[str, float]):
        """重置峰值为当前总资产（止损恢复后调用，避免立即再次触发止损）"""
        self.peak_value = self.get_total_value(prices)

    def emergency_liquidate(self, prices: dict[str, float], date: str) -> list[Order]:
        """紧急清仓"""
        orders = []
        for code, shares in list(self.positions.items()):
            price = prices.get(code, 0)
            order = self._sell(code, shares, price, date)
            if order:
                orders.append(order)
        return orders
