"""回测模拟器：逐日循环 + Headless / 双 Agent 模式"""

from __future__ import annotations

from datetime import datetime, timedelta

from stock_agent.config import (
    INITIAL_CAPITAL,
    MAX_DRAWDOWN_STOP,
    STOP_COOLDOWN_DAYS,
    ETF_POOL,
    TOP_N,
    DATA_START,
    DATA_END,
    BACKTEST_START,
)
from stock_agent.data.fetcher import DataFetcher
from stock_agent.data.feed import MarketFeed
from stock_agent.strategy.momentum import rank_etfs, generate_target_weights
from stock_agent.engine.portfolio import Portfolio
from stock_agent.engine.performance import PerformanceTracker
from stock_agent.logging_.logger import TradingLogger
from stock_agent.agent.collaboration import DualAgentCoordinator


class BacktestSimulator:
    def __init__(
        self,
        backtest_start: str | None = None,
        data_end: str | None = None,
    ):
        self._backtest_start = backtest_start or BACKTEST_START
        self._data_end = data_end or DATA_END
        # data_start 往前推 2 个月，确保动量窗口有足够数据
        bt = datetime.strptime(self._backtest_start, "%Y%m%d")
        self._data_start = (bt - timedelta(days=60)).strftime("%Y%m%d")

        self.fetcher = DataFetcher(start=self._data_start, end=self._data_end)
        self.portfolio = Portfolio(INITIAL_CAPITAL)
        self.tracker = PerformanceTracker(INITIAL_CAPITAL)
        self.logger = TradingLogger()

        self.all_data: dict | None = None
        self.feed: MarketFeed | None = None

    def _init_data(self):
        if self.all_data is None:
            self.all_data = self.fetcher.fetch_all()
            self.feed = MarketFeed(self.all_data, backtest_start=self._backtest_start)

    def run_headless(self) -> dict:
        """纯策略回测，无 LLM 调用。"""
        self._init_data()
        assert self.feed is not None

        print(f"\n{'=' * 50}")
        print(f"开始 Headless 回测 (共 {self.feed.total_days} 个交易日)")
        print(f"{'=' * 50}\n")

        stop_triggered = False
        cooldown_remaining = 0

        while self.feed.advance():
            date = self.feed.current_date_str
            prices = self.feed.get_today_prices()
            if not prices:
                continue

            self.tracker.record(date, self.portfolio, prices)

            if stop_triggered and cooldown_remaining > 0:
                cooldown_remaining -= 1
                if cooldown_remaining == 0:
                    stop_triggered = False
                    self.portfolio.reset_peak(prices)
                    print(f"[{date}] [INFO] 冷却期结束，恢复交易")

            dd = self.portfolio.check_drawdown(prices)
            if dd <= MAX_DRAWDOWN_STOP and not stop_triggered:
                print(f"[{date}] [WARN] 回撤 {dd:.2%} 触发止损线，紧急清仓，进入 {STOP_COOLDOWN_DAYS} 日冷却期")
                orders = self.portfolio.emergency_liquidate(prices, date)
                for order in orders:
                    self.logger.log_trade(order)
                self.logger.log_emergency(date, orders, dd)
                stop_triggered = True
                cooldown_remaining = STOP_COOLDOWN_DAYS
                continue

            if self.feed.is_rebalance_day() and not stop_triggered:
                rankings = rank_etfs(self.feed)
                weights = generate_target_weights(rankings)
                orders = self.portfolio.rebalance_to(weights, prices, date)

                for order in orders:
                    self.logger.log_trade(order)

                top_names = [f"{ETF_POOL.get(code, code)}({momentum:+.4f})" for code, momentum in rankings[:TOP_N]]
                all_negative = all(momentum <= 0 for _, momentum in rankings[:TOP_N])
                if all_negative:
                    reasoning = f"动量前{TOP_N}: {', '.join(top_names)}，均为负动量，全仓安全资产"
                else:
                    alloc = [
                        f"{ETF_POOL.get(code, code)} {weight:.0%}"
                        for code, weight in sorted(weights.items(), key=lambda item: -item[1])
                    ]
                    reasoning = f"动量前{TOP_N}: {', '.join(top_names)}，配置: {', '.join(alloc)}"
                self.logger.log_decision(date, rankings, weights, reasoning)

                if orders:
                    total = self.portfolio.get_total_value(prices)
                    print(f"[{date}] 调仓 -> ", end="")
                    for code, weight in sorted(weights.items(), key=lambda item: -item[1]):
                        print(f"{ETF_POOL.get(code, code)} {weight:.0%} ", end="")
                    print(f"| 总资产 {total:,.0f}元")

            nav = self.portfolio.get_total_value(prices)
            self.logger.log_daily(date, nav, self.portfolio.cash, dict(self.portfolio.positions), dd)

        metrics = self.tracker.get_metrics()
        metrics["total_trades"] = len(self.portfolio.order_history)
        self.logger.save_all()

        self._print_summary(metrics)
        return metrics

    def run_agent(self) -> dict:
        """双 Agent 模式回测：LM Studio 金融子 Agent + 主 Agent 加权裁决。"""
        self._init_data()
        assert self.feed is not None

        coordinator = DualAgentCoordinator(
            feed=self.feed,
            portfolio=self.portfolio,
            logger=self.logger,
        )

        print(f"\n{'=' * 50}")
        print(f"开始 Agent 回测 (共 {self.feed.total_days} 个交易日)")
        print(f"{'=' * 50}\n")

        stop_triggered = False
        cooldown_remaining = 0

        while self.feed.advance():
            date = self.feed.current_date_str
            prices = self.feed.get_today_prices()
            if not prices:
                continue

            self.tracker.record(date, self.portfolio, prices)

            if stop_triggered and cooldown_remaining > 0:
                cooldown_remaining -= 1
                if cooldown_remaining == 0:
                    stop_triggered = False
                    self.portfolio.reset_peak(prices)
                    print(f"[{date}] [INFO] 冷却期结束，恢复交易")

            dd = self.portfolio.check_drawdown(prices)
            if dd <= MAX_DRAWDOWN_STOP and not stop_triggered:
                print(f"[{date}] [WARN] 回撤触发止损，进入 {STOP_COOLDOWN_DAYS} 日冷却期")
                orders = self.portfolio.emergency_liquidate(prices, date)
                for order in orders:
                    self.logger.log_trade(order)
                self.logger.log_emergency(date, orders, dd)
                stop_triggered = True
                cooldown_remaining = STOP_COOLDOWN_DAYS
                continue

            if self.feed.is_rebalance_day() and not stop_triggered:
                print(f"\n[{date}] [INFO] 调仓日 - 双 Agent 开始协同分析...")
                decision = coordinator.run_rebalance_cycle()

                alloc = ", ".join(
                    f"{ETF_POOL.get(code, code)} {weight:.0%}"
                    for code, weight in sorted(decision.target_weights.items(), key=lambda item: -item[1])
                )
                print(
                    f"[{date}] 子 Agent({decision.sub_agent.source}) + 主 Agent({decision.main_agent.source}) "
                    f"-> {decision.execution_status} | 目标配置: {alloc}"
                )

            nav = self.portfolio.get_total_value(prices)
            self.logger.log_daily(date, nav, self.portfolio.cash, dict(self.portfolio.positions), dd)

        metrics = self.tracker.get_metrics()
        metrics["total_trades"] = len(self.portfolio.order_history)
        self.logger.save_all()

        self._print_summary(metrics)
        return metrics

    def _print_summary(self, metrics: dict):
        print(f"\n{'=' * 50}")
        print("回测结果摘要")
        print(f"{'=' * 50}")
        print(f"初始资金: {metrics.get('initial_capital', 0):,.2f}元")
        print(f"最终资产: {metrics.get('final_value', 0):,.2f}元")
        print(f"总收益率: {metrics.get('total_return', 0):+.2f}%")
        print(f"年化收益: {metrics.get('annualized_return', 0):+.2f}%")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"总交易次数: {metrics.get('total_trades', 0)}")
        print(f"{'=' * 50}\n")
