"""服务端共享状态：保存回测结果供 API 读取（支持 headless + agent 双模式）"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from stock_agent.data.feed import MarketFeed
from stock_agent.engine.portfolio import Portfolio
from stock_agent.engine.performance import PerformanceTracker
from stock_agent.logging_.logger import TradingLogger


@dataclass
class BacktestState:
    feed: MarketFeed
    portfolio: Portfolio
    tracker: PerformanceTracker
    logger: TradingLogger
    last_prices: dict[str, float] = field(default_factory=dict)
    data_sources: dict[str, str] = field(default_factory=dict)


@dataclass
class DualBacktestState:
    headless: BacktestState | None = None
    agent: BacktestState | None = None
    agent_status: str = "pending"  # pending / running / completed / failed
    agent_error: str | None = None


_dual = DualBacktestState()


def get_state() -> BacktestState | None:
    """向后兼容：返回 headless 回测结果"""
    return _dual.headless


def get_dual_state() -> DualBacktestState:
    return _dual


def _extract_last_prices(feed: MarketFeed) -> dict[str, float]:
    """从 feed 中提取最后一个交易日的收盘价"""
    last_prices: dict[str, float] = {}
    if feed and feed._trading_dates:
        last_date = feed._trading_dates[-1]
        for ts_code, df in feed._all_data.items():
            row = df[pd.to_datetime(df["trade_date"]) == last_date]
            if not row.empty:
                last_prices[ts_code] = float(row.iloc[0]["close"])
    return last_prices


def run_headless_and_store() -> BacktestState:
    """运行 headless 回测并保存结果"""
    from stock_agent.backtest.simulator import BacktestSimulator

    sim = BacktestSimulator()
    sim.run_headless()

    state = BacktestState(
        feed=sim.feed,
        portfolio=sim.portfolio,
        tracker=sim.tracker,
        logger=sim.logger,
        last_prices=_extract_last_prices(sim.feed),
        data_sources=sim.fetcher.sources_by_code,
    )
    _dual.headless = state
    return state


def run_agent_and_store():
    """运行 agent 回测并保存结果（设计为在后台线程中调用）"""
    from stock_agent.backtest.simulator import BacktestSimulator

    _dual.agent_status = "running"
    try:
        headless = _dual.headless
        if headless is None:
            raise RuntimeError("Headless 回测尚未完成")

        # 复用 headless 的市场数据（只读），创建独立的引擎组件
        sim = BacktestSimulator()
        sim.all_data = headless.feed._all_data
        sim.feed = MarketFeed(sim.all_data)
        sim.run_agent()

        state = BacktestState(
            feed=sim.feed,
            portfolio=sim.portfolio,
            tracker=sim.tracker,
            logger=sim.logger,
            last_prices=_extract_last_prices(sim.feed),
            data_sources=headless.data_sources,
        )
        _dual.agent = state
        _dual.agent_status = "completed"
        print("[Server] Agent 回测完成")
    except Exception as e:
        _dual.agent_status = "failed"
        _dual.agent_error = str(e)
        print(f"[Server] Agent 回测失败: {e}")
