"""组合管理单元测试"""

import pytest

from stock_agent.engine.portfolio import Portfolio, Order


class TestGetTotalValue:
    def test_cash_only(self):
        p = Portfolio(100_000)
        assert p.get_total_value({}) == 100_000

    def test_with_positions(self):
        p = Portfolio(50_000)
        p.positions = {"A": 1000, "B": 500}
        prices = {"A": 10.0, "B": 20.0}
        # 50000 + 1000*10 + 500*20 = 70000
        assert p.get_total_value(prices) == 70_000


class TestCheckDrawdown:
    def test_no_drawdown(self):
        p = Portfolio(100_000)
        dd = p.check_drawdown({})
        assert dd == 0.0

    def test_with_drawdown(self):
        p = Portfolio(100_000)
        p.peak_value = 100_000
        # 模拟亏损: cash 下降到 90000
        p.cash = 90_000
        dd = p.check_drawdown({})
        assert abs(dd - (-0.10)) < 1e-9

    def test_peak_updates(self):
        p = Portfolio(100_000)
        p.cash = 110_000
        dd = p.check_drawdown({})
        assert dd == 0.0
        assert p.peak_value == 110_000


class TestRebalance:
    def test_buy_from_cash(self):
        """从纯现金状态买入"""
        p = Portfolio(100_000)
        prices = {"A": 10.0}
        orders = p.rebalance_to({"A": 1.0}, prices, "2025-01-01")
        assert len(orders) == 1
        assert orders[0].direction == "BUY"
        assert orders[0].shares > 0
        # 手数应是 100 的整数倍
        assert orders[0].shares % 100 == 0

    def test_sell_all(self):
        """全部卖出"""
        p = Portfolio(0)
        p.cash = 0
        p.positions = {"A": 1000}
        p.cost_basis = {"A": 10.0}
        prices = {"A": 10.0}
        orders = p.rebalance_to({}, prices, "2025-01-01")
        assert len(orders) == 1
        assert orders[0].direction == "SELL"
        assert orders[0].shares == 1000
        assert p.positions.get("A") is None

    def test_commission_deducted(self):
        """佣金正确扣除"""
        p = Portfolio(100_000)
        prices = {"A": 10.0}
        p.rebalance_to({"A": 1.0}, prices, "2025-01-01")
        # 现金 + 持仓市值 应略低于初始值（因为佣金）
        total = p.get_total_value(prices)
        assert total < 100_000

    def test_lot_size(self):
        """买入股数是 100 的倍数"""
        p = Portfolio(1_000_000)
        prices = {"A": 3.567}
        p.rebalance_to({"A": 1.0}, prices, "2025-01-01")
        assert p.positions.get("A", 0) % 100 == 0


class TestEmergencyLiquidate:
    def test_liquidate_all(self):
        p = Portfolio(10_000)
        p.positions = {"A": 500, "B": 300}
        p.cost_basis = {"A": 10.0, "B": 20.0}
        prices = {"A": 10.0, "B": 20.0}
        orders = p.emergency_liquidate(prices, "2025-01-01")
        assert len(orders) == 2
        assert all(o.direction == "SELL" for o in orders)
        assert len(p.positions) == 0


class TestResetPeak:
    def test_reset(self):
        p = Portfolio(100_000)
        p.peak_value = 120_000
        p.cash = 90_000
        p.reset_peak({})
        assert p.peak_value == 90_000
