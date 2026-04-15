"""动量策略单元测试"""

import math

import pandas as pd
import pytest

from stock_agent.strategy.momentum import calc_momentum, generate_target_weights
from stock_agent.config import SAFE_ASSET


# ---- calc_momentum ----

class TestCalcMomentum:
    def test_normal(self):
        """正常计算: (last / first) - 1"""
        prices = pd.Series([100.0] * 20 + [120.0])  # 21个数据点, window=20
        result = calc_momentum(prices, window=20)
        assert abs(result - 0.2) < 1e-9

    def test_negative(self):
        prices = pd.Series([100.0] * 20 + [80.0])
        result = calc_momentum(prices, window=20)
        assert abs(result - (-0.2)) < 1e-9

    def test_insufficient_data(self):
        """数据不足时返回 NaN"""
        prices = pd.Series([100.0] * 10)  # 10 < 20+1
        result = calc_momentum(prices, window=20)
        assert math.isnan(result)

    def test_zero_change(self):
        prices = pd.Series([50.0] * 21)
        result = calc_momentum(prices, window=20)
        assert result == 0.0


# ---- generate_target_weights ----

class TestGenerateTargetWeights:
    def test_all_positive(self):
        """前N名均为正动量 → 等权配置"""
        ranked = [("A", 0.10), ("B", 0.05), ("C", -0.01)]
        weights = generate_target_weights(ranked, top_n=2, safe_asset="SAFE", max_single=0.50)
        assert abs(weights.get("A", 0) - 0.50) < 1e-9
        assert abs(weights.get("B", 0) - 0.50) < 1e-9
        assert "SAFE" not in weights

    def test_all_negative(self):
        """前N名均为负动量 → 100% 安全资产"""
        ranked = [("A", -0.01), ("B", -0.05)]
        weights = generate_target_weights(ranked, top_n=2, safe_asset="SAFE", max_single=0.50)
        assert weights == {"SAFE": 1.0}

    def test_partial_negative(self):
        """部分负动量 → 只持有正动量标的"""
        ranked = [("A", 0.10), ("B", -0.05), ("C", -0.10)]
        weights = generate_target_weights(ranked, top_n=2, safe_asset="SAFE", max_single=0.50)
        # A 是唯一正动量, 权重=1.0, 但被 max_single=0.50 限制
        assert abs(weights.get("A", 0) - 0.50) < 1e-9
        assert abs(weights.get("SAFE", 0) - 0.50) < 1e-9

    def test_max_weight_cap(self):
        """单只超过最大权重 → 多余部分给安全资产"""
        ranked = [("A", 0.20)]
        weights = generate_target_weights(ranked, top_n=1, safe_asset="SAFE", max_single=0.50)
        assert abs(weights.get("A", 0) - 0.50) < 1e-9
        assert abs(weights.get("SAFE", 0) - 0.50) < 1e-9

    def test_empty_rankings(self):
        """空排名 → 100% 安全资产"""
        weights = generate_target_weights([], safe_asset="SAFE")
        assert weights == {"SAFE": 1.0}
