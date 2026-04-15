"""回测模拟器：逐日循环 + Agent/Headless 双模式"""

from __future__ import annotations

from stock_agent.config import (
    INITIAL_CAPITAL,
    MAX_DRAWDOWN_STOP,
    STOP_COOLDOWN_DAYS,
    ETF_POOL,
    TOP_N,
)
from stock_agent.data.fetcher import DataFetcher
from stock_agent.data.feed import MarketFeed
from stock_agent.strategy.momentum import rank_etfs, generate_target_weights
from stock_agent.engine.portfolio import Portfolio
from stock_agent.engine.performance import PerformanceTracker
from stock_agent.logging_.logger import TradingLogger
from stock_agent.agent.tools import TradingToolkit
from stock_agent.agent.trading_agent import create_trading_agent


class BacktestSimulator:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.portfolio = Portfolio(INITIAL_CAPITAL)
        self.tracker = PerformanceTracker(INITIAL_CAPITAL)
        self.logger = TradingLogger()

        # 数据需要先获取
        self.all_data: dict | None = None
        self.feed: MarketFeed | None = None

    def _init_data(self):
        if self.all_data is None:
            self.all_data = self.fetcher.fetch_all()
            self.feed = MarketFeed(self.all_data)

    def run_headless(self) -> dict:
        """纯策略回测，无 LLM 调用"""
        self._init_data()
        assert self.feed is not None

        print(f"\n{'='*50}")
        print(f"开始 Headless 回测 (共 {self.feed.total_days} 个交易日)")
        print(f"{'='*50}\n")

        stop_triggered = False
        cooldown_remaining = 0

        while self.feed.advance():
            date = self.feed.current_date_str
            prices = self.feed.get_today_prices()
            if not prices:
                continue

            # 记录每日净值
            self.tracker.record(date, self.portfolio, prices)

            # 冷却期倒计时
            if stop_triggered and cooldown_remaining > 0:
                cooldown_remaining -= 1
                if cooldown_remaining == 0:
                    stop_triggered = False
                    self.portfolio.reset_peak(prices)
                    print(f"[{date}] ✅ 冷却期结束，恢复交易")

            # 检查回撤止损
            dd = self.portfolio.check_drawdown(prices)
            if dd <= MAX_DRAWDOWN_STOP and not stop_triggered:
                print(f"[{date}] ⚠ 回撤 {dd:.2%} 触发止损线，紧急清仓，进入 {STOP_COOLDOWN_DAYS} 日冷却期")
                orders = self.portfolio.emergency_liquidate(prices, date)
                for o in orders:
                    self.logger.log_trade(o)
                self.logger.log_emergency(date, orders, dd)
                stop_triggered = True
                cooldown_remaining = STOP_COOLDOWN_DAYS
                continue

            # 调仓日执行策略
            if self.feed.is_rebalance_day() and not stop_triggered:
                rankings = rank_etfs(self.feed)
                weights = generate_target_weights(rankings)
                orders = self.portfolio.rebalance_to(weights, prices, date)

                for o in orders:
                    self.logger.log_trade(o)

                # 生成 reasoning
                top_names = [f"{ETF_POOL.get(c, c)}({m:+.4f})" for c, m in rankings[:TOP_N]]
                all_negative = all(m <= 0 for _, m in rankings[:TOP_N])
                if all_negative:
                    reasoning = f"动量前{TOP_N}: {', '.join(top_names)}，均为负动量，全仓安全资产"
                else:
                    alloc = [f"{ETF_POOL.get(c, c)} {w:.0%}" for c, w in sorted(weights.items(), key=lambda x: -x[1])]
                    reasoning = f"动量前{TOP_N}: {', '.join(top_names)}，配置: {', '.join(alloc)}"
                self.logger.log_decision(date, rankings, weights, reasoning)

                if orders:
                    total = self.portfolio.get_total_value(prices)
                    print(f"[{date}] 调仓 → ", end="")
                    for code, w in sorted(weights.items(), key=lambda x: -x[1]):
                        print(f"{ETF_POOL.get(code, code)} {w:.0%} ", end="")
                    print(f"| 总资产 {total:,.0f}元")

            # 每日日志
            nav = self.portfolio.get_total_value(prices)
            self.logger.log_daily(date, nav, self.portfolio.cash,
                                  dict(self.portfolio.positions), dd)

        # 最终结果
        metrics = self.tracker.get_metrics()
        metrics["total_trades"] = len(self.portfolio.order_history)
        self.logger.save_all()

        self._print_summary(metrics)
        return metrics

    def run_agent(self) -> dict:
        """Agent 模式回测，LLM 自主决策"""
        self._init_data()
        assert self.feed is not None

        toolkit = TradingToolkit(self.feed, self.portfolio, self.tracker, self.logger)
        agent = create_trading_agent(toolkit)

        print(f"\n{'='*50}")
        print(f"开始 Agent 回测 (共 {self.feed.total_days} 个交易日)")
        print(f"{'='*50}\n")

        stop_triggered = False
        cooldown_remaining = 0

        while self.feed.advance():
            date = self.feed.current_date_str
            prices = self.feed.get_today_prices()
            if not prices:
                continue

            self.tracker.record(date, self.portfolio, prices)

            # 冷却期倒计时
            if stop_triggered and cooldown_remaining > 0:
                cooldown_remaining -= 1
                if cooldown_remaining == 0:
                    stop_triggered = False
                    self.portfolio.reset_peak(prices)
                    print(f"[{date}] ✅ 冷却期结束，恢复交易")
                    agent.print_response(
                        f"通知：{date} 冷却期已结束，组合恢复正常交易。",
                        stream=True,
                    )

            # 检查回撤止损
            dd = self.portfolio.check_drawdown(prices)
            if dd <= MAX_DRAWDOWN_STOP and not stop_triggered:
                print(f"[{date}] ⚠ 回撤触发止损，进入 {STOP_COOLDOWN_DAYS} 日冷却期")
                orders = self.portfolio.emergency_liquidate(prices, date)
                for o in orders:
                    self.logger.log_trade(o)
                self.logger.log_emergency(date, orders, dd)
                stop_triggered = True
                cooldown_remaining = STOP_COOLDOWN_DAYS

                agent.print_response(
                    f"紧急通知：{date} 组合回撤达到 {dd:.2%}，已触发-8%止损线，"
                    f"执行了紧急清仓，进入 {STOP_COOLDOWN_DAYS} 个交易日冷却期。请分析原因。",
                    stream=True,
                )
                continue

            # 调仓日让 Agent 决策
            if self.feed.is_rebalance_day() and not stop_triggered:
                print(f"\n[{date}] 📊 调仓日 - Agent 开始分析...")
                agent.print_response(
                    f"今天是 {date}（调仓日）。请分析当前市场并执行调仓。"
                    f"按照以下步骤操作：\n"
                    f"1. 查看动量排名\n"
                    f"2. 查看算法推荐配置（仅供参考）\n"
                    f"3. 查看当前持仓\n"
                    f"4. 根据你自己的分析判断，用 execute_custom_rebalance 设定你认为最优的权重配置\n"
                    f"你不需要照搬算法推荐，请给出你自己的配置和理由。",
                    stream=True,
                )

            # 每日日志
            nav = self.portfolio.get_total_value(prices)
            self.logger.log_daily(date, nav, self.portfolio.cash,
                                  dict(self.portfolio.positions), dd)

        metrics = self.tracker.get_metrics()
        metrics["total_trades"] = len(self.portfolio.order_history)
        self.logger.save_all()

        # 让 Agent 总结
        agent.print_response(
            "回测已结束。请调用 get_performance_summary 查看绩效指标，并给出整体总结。",
            stream=True,
        )

        self._print_summary(metrics)
        return metrics

    def _print_summary(self, metrics: dict):
        print(f"\n{'='*50}")
        print("回测结果摘要")
        print(f"{'='*50}")
        print(f"初始资金: {metrics.get('initial_capital', 0):,.2f}元")
        print(f"最终资产: {metrics.get('final_value', 0):,.2f}元")
        print(f"总收益率: {metrics.get('total_return', 0):+.2f}%")
        print(f"年化收益: {metrics.get('annualized_return', 0):+.2f}%")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"总交易次数: {metrics.get('total_trades', 0)}")
        print(f"{'='*50}\n")
