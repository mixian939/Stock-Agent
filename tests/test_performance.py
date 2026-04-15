"""绩效指标单元测试"""

import pytest

from stock_agent.engine.performance import PerformanceTracker
from stock_agent.engine.portfolio import Portfolio


class TestPerformanceTracker:
    def _make_tracker_with_data(self) -> PerformanceTracker:
        """构造一个有 5 天数据的 tracker"""
        tracker = PerformanceTracker(100_000)
        portfolio = Portfolio(100_000)

        # 模拟 5 天净值变化: 100000 → 101000 → 102000 → 101500 → 103000
        navs = [100_000, 101_000, 102_000, 101_500, 103_000]
        for i, nav in enumerate(navs):
            portfolio.cash = nav
            portfolio.positions = {}
            tracker.record(f"2025-01-{i+1:02d}", portfolio, {})

        return tracker

    def test_insufficient_data(self):
        tracker = PerformanceTracker(100_000)
        result = tracker.get_metrics()
        assert "error" in result

    def test_total_return(self):
        tracker = self._make_tracker_with_data()
        metrics = tracker.get_metrics()
        # (103000 / 100000 - 1) * 100 = 3.0%
        assert abs(metrics["total_return"] - 3.0) < 0.1

    def test_final_value(self):
        tracker = self._make_tracker_with_data()
        metrics = tracker.get_metrics()
        assert metrics["final_value"] == 103_000

    def test_max_drawdown(self):
        tracker = self._make_tracker_with_data()
        metrics = tracker.get_metrics()
        # 峰值 102000, 回撤到 101500: (101500/102000 - 1) ≈ -0.49%
        assert metrics["max_drawdown"] < 0

    def test_trading_days(self):
        tracker = self._make_tracker_with_data()
        metrics = tracker.get_metrics()
        assert metrics["trading_days"] == 5

    def test_sharpe_is_float(self):
        tracker = self._make_tracker_with_data()
        metrics = tracker.get_metrics()
        assert isinstance(metrics["sharpe_ratio"], float)

    def test_to_dataframe(self):
        tracker = self._make_tracker_with_data()
        df = tracker.to_dataframe()
        assert len(df) == 5
        assert "nav" in df.columns
        assert "drawdown" in df.columns
