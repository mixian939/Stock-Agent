"""动量轮动策略：纯函数，无状态"""

from __future__ import annotations

import math

import pandas as pd

from stock_agent.config import (
    ETF_POOL,
    MOMENTUM_WINDOW,
    TOP_N,
    SAFE_ASSET,
    MAX_SINGLE_WEIGHT,
)
from stock_agent.data.feed import MarketFeed


def calc_momentum(prices: pd.Series, window: int = MOMENTUM_WINDOW) -> float:
    """计算动量 = (今日收盘 / window日前收盘) - 1"""
    if len(prices) < window + 1:
        return float("nan")
    return float(prices.iloc[-1] / prices.iloc[-(window + 1)] - 1)


def rank_etfs(
    feed: MarketFeed,
    etf_codes: list[str] | None = None,
    window: int = MOMENTUM_WINDOW,
) -> list[tuple[str, float]]:
    """对 ETF 池按动量降序排名，返回 [(ts_code, momentum), ...]"""
    if etf_codes is None:
        etf_codes = list(ETF_POOL.keys())

    rankings = []
    for code in etf_codes:
        hist = feed.get_history(code, lookback=window + 5)  # 多取几天容错
        if hist.empty:
            continue
        m = calc_momentum(hist["close"], window)
        if not math.isnan(m):
            rankings.append((code, m))

    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings


def generate_target_weights(
    ranked: list[tuple[str, float]],
    top_n: int = TOP_N,
    safe_asset: str = SAFE_ASSET,
    max_single: float = MAX_SINGLE_WEIGHT,
) -> dict[str, float]:
    """
    核心轮动逻辑：
    1. 前 top_n 名动量均为负 → 100% 安全资产
    2. 否则等权持有前 top_n
    3. 限制单只最大权重
    """
    if not ranked:
        return {safe_asset: 1.0}

    top = ranked[:top_n]
    # 检查是否全部为负动量
    if all(m <= 0 for _, m in top):
        return {safe_asset: 1.0}

    # 等权分配
    weights: dict[str, float] = {}
    n = min(top_n, len(top))
    base_weight = 1.0 / n

    for code, momentum in top:
        if momentum > 0:
            weights[code] = base_weight

    # 若筛掉了负动量的，重新分配
    if weights:
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

    # 限制单只最大权重
    for code in list(weights.keys()):
        if weights[code] > max_single:
            excess = weights[code] - max_single
            weights[code] = max_single
            # 将多余部分分配给安全资产
            weights[safe_asset] = weights.get(safe_asset, 0) + excess

    return weights
