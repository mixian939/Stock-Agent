"""双 Agent 协调与分类 ETF 池单元测试"""

from __future__ import annotations

import pandas as pd

from stock_agent.agent.collaboration import (
    combine_scores,
    normalize_weights,
    score_weighted_allocation,
)
from stock_agent.data.feed import MarketFeed
from stock_agent.strategy.momentum import rank_etfs


def _make_df(ts_code: str, closes: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2025-01-02", periods=len(closes), freq="B")
    return pd.DataFrame(
        {
            "ts_code": ts_code,
            "trade_date": dates,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "pct_chg": [0.0] * len(closes),
        }
    )


class TestCategoryRanking:
    def test_rank_etfs_collapse_by_category(self):
        feed = MarketFeed(
            {
                "510300.SH": _make_df("510300.SH", [100.0] * 20 + [110.0]),
                "159919.SZ": _make_df("159919.SZ", [100.0] * 20 + [120.0]),
                "511010.SH": _make_df("511010.SH", [100.0] * 20 + [101.0]),
                "511260.SH": _make_df("511260.SH", [100.0] * 20 + [102.0]),
            }
        )
        for _ in range(feed.total_days):
            feed.advance()

        rankings = rank_etfs(feed)

        assert len(rankings) == 2
        assert rankings[0][0] == "159919.SZ"
        assert rankings[1][0] == "511260.SH"

    def test_rank_etfs_without_collapse_returns_all_candidates(self):
        feed = MarketFeed(
            {
                "510300.SH": _make_df("510300.SH", [100.0] * 20 + [110.0]),
                "159919.SZ": _make_df("159919.SZ", [100.0] * 20 + [120.0]),
            }
        )
        for _ in range(feed.total_days):
            feed.advance()

        rankings = rank_etfs(feed, collapse_by_category=False)

        assert len(rankings) == 2
        assert [code for code, _ in rankings] == ["159919.SZ", "510300.SH"]


class TestDualAgentScoring:
    def test_combine_scores_uses_60_40_weights(self):
        combined = combine_scores(
            sub_scores={"A": 80, "B": 40},
            main_scores={"A": 50, "B": 70},
        )

        assert combined["A"] == 68.0
        assert combined["B"] == 52.0

    def test_score_weighted_allocation_falls_back_to_safe_asset(self):
        weights = score_weighted_allocation(
            scores={"A": 50, "B": 54},
            safe_asset="SAFE",
            top_n=2,
        )
        assert weights == {"SAFE": 1.0}

    def test_normalize_weights_filters_invalid_codes_and_renormalizes(self):
        weights = normalize_weights(
            allowed_codes=["A", "B", "SAFE"],
            raw_weights={"A": 0.7, "X": 0.3},
            safe_asset="SAFE",
            fallback_weights={"SAFE": 1.0},
        )
        assert weights == {"A": 0.5, "SAFE": 0.5}
