"""动量轮动策略：纯函数，无状态"""

from __future__ import annotations

import math

import pandas as pd

from stock_agent.config import (
    ETF_POOL,
    ETF_CATEGORIES,
    MOMENTUM_WINDOW,
    TOP_N,
    SAFE_ASSET,
    SAFE_ASSET_CATEGORY,
    MAX_SINGLE_WEIGHT,
)
from stock_agent.data.feed import MarketFeed


def calc_momentum(prices: pd.Series, window: int = MOMENTUM_WINDOW) -> float:
    """计算动量 = (今日收盘 / window 日前收盘) - 1"""
    if len(prices) < window + 1:
        return float("nan")
    return float(prices.iloc[-1] / prices.iloc[-(window + 1)] - 1)


def rank_etfs(
    feed: MarketFeed,
    etf_codes: list[str] | None = None,
    window: int = MOMENTUM_WINDOW,
    collapse_by_category: bool = True,
) -> list[tuple[str, float]]:
    """按动量降序排名。

    默认会先在每个资产类别中选出动量最强的 1 只 ETF，
    这样 ETF 池扩容后仍然保持 7 个资产类别之间的轮动逻辑。
    """
    if etf_codes is None:
        etf_codes = list(ETF_POOL.keys())

    raw_rankings: list[tuple[str, float]] = []
    for code in etf_codes:
        hist = feed.get_history(code, lookback=window + 5)
        if hist.empty:
            continue
        momentum = calc_momentum(hist["close"], window)
        if not math.isnan(momentum):
            raw_rankings.append((code, momentum))

    raw_rankings.sort(key=lambda item: item[1], reverse=True)
    if not collapse_by_category:
        return raw_rankings

    category_best: dict[str, tuple[str, float]] = {}
    for code, momentum in raw_rankings:
        category = ETF_CATEGORIES.get(code, code)
        if category not in category_best:
            category_best[category] = (code, momentum)

    collapsed = list(category_best.values())
    collapsed.sort(key=lambda item: item[1], reverse=True)
    return collapsed


def resolve_safe_asset(
    ranked: list[tuple[str, float]],
    default_safe_asset: str = SAFE_ASSET,
) -> str:
    """在国债类别中优先选择当前动量更优的安全资产。"""
    treasury_candidates = [
        (code, momentum)
        for code, momentum in ranked
        if ETF_CATEGORIES.get(code) == SAFE_ASSET_CATEGORY
    ]
    if not treasury_candidates:
        return default_safe_asset
    treasury_candidates.sort(key=lambda item: item[1], reverse=True)
    return treasury_candidates[0][0]


def generate_target_weights(
    ranked: list[tuple[str, float]],
    top_n: int = TOP_N,
    safe_asset: str = SAFE_ASSET,
    max_single: float = MAX_SINGLE_WEIGHT,
) -> dict[str, float]:
    """
    核心轮动逻辑：
    1. 前 top_n 名动量均为负 -> 100% 安全资产
    2. 否则等权持有前 top_n 名中的正动量标的
    3. 限制单只最大权重，超出部分给安全资产
    """
    dynamic_safe_asset = resolve_safe_asset(ranked, default_safe_asset=safe_asset)

    if not ranked:
        return {dynamic_safe_asset: 1.0}

    top = ranked[:top_n]
    if all(momentum <= 0 for _, momentum in top):
        return {dynamic_safe_asset: 1.0}

    weights: dict[str, float] = {}
    n = min(top_n, len(top))
    base_weight = 1.0 / n if n > 0 else 1.0

    for code, momentum in top:
        if momentum > 0:
            weights[code] = base_weight

    if weights:
        total = sum(weights.values())
        weights = {code: weight / total for code, weight in weights.items()}

    for code in list(weights.keys()):
        if weights[code] > max_single:
            excess = weights[code] - max_single
            weights[code] = max_single
            weights[dynamic_safe_asset] = weights.get(dynamic_safe_asset, 0) + excess

    return weights or {dynamic_safe_asset: 1.0}
