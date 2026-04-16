"""Agno Toolkit：策略/引擎与 Agent 的桥梁"""

from __future__ import annotations

import json

from agno.tools import Toolkit

from stock_agent.config import ETF_POOL, ETF_CATEGORIES, MOMENTUM_WINDOW
from stock_agent.data.feed import MarketFeed
from stock_agent.strategy.momentum import rank_etfs, generate_target_weights
from stock_agent.engine.portfolio import Portfolio
from stock_agent.engine.performance import PerformanceTracker
from stock_agent.logging_.logger import TradingLogger


class TradingToolkit(Toolkit):
    def __init__(
        self,
        feed: MarketFeed,
        portfolio: Portfolio,
        tracker: PerformanceTracker,
        logger: TradingLogger,
    ):
        super().__init__(name="trading_tools")
        self.feed = feed
        self.portfolio = portfolio
        self.tracker = tracker
        self.logger = logger
        self._last_rankings: list[tuple[str, float]] = []
        self._last_weights: dict[str, float] = {}

        self.register(self.get_current_date)
        self.register(self.get_market_data)
        self.register(self.get_momentum_rankings)
        self.register(self.get_portfolio_status)
        self.register(self.get_recommended_allocation)
        self.register(self.execute_rebalance)
        self.register(self.execute_custom_rebalance)
        self.register(self.get_performance_summary)
        self.register(self.check_if_rebalance_day)

    def get_current_date(self) -> str:
        """获取当前模拟日期。"""
        current_date = self.feed.current_date
        if current_date is None:
            return "模拟尚未开始"
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"当前日期: {current_date.strftime('%Y-%m-%d')} ({weekdays[current_date.weekday()]})"

    def get_market_data(self, ts_code: str, lookback: int = 10) -> str:
        """获取指定 ETF 近期行情数据。"""
        name = ETF_POOL.get(ts_code, ts_code)
        category = ETF_CATEGORIES.get(ts_code, "未知分类")
        hist = self.feed.get_history(ts_code, lookback)
        if hist.empty:
            return f"{name} ({ts_code}) 无数据"

        lines = [f"=== {name} ({ts_code}) / {category} / 近 {len(hist)} 日行情 ==="]
        lines.append("日期 | 开盘 | 最高 | 最低 | 收盘 | 涨跌幅%")
        for _, row in hist.iterrows():
            date_str = row["trade_date"]
            if hasattr(date_str, "strftime"):
                date_str = date_str.strftime("%m-%d")
            pct = row.get("pct_chg", 0.0)
            lines.append(
                f"{date_str} | {row['open']:.3f} | {row['high']:.3f} | "
                f"{row['low']:.3f} | {row['close']:.3f} | {pct:+.2f}%"
            )
        return "\n".join(lines)

    def get_momentum_rankings(self) -> str:
        """计算 7 个资产类别代表 ETF 的 20 日动量排名。"""
        rankings = rank_etfs(self.feed)
        self._last_rankings = rankings

        lines = [f"=== 类别代表 ETF 动量排名 ({self.feed.current_date_str}) ==="]
        if not rankings:
            lines.append(f"当前数据不足 {MOMENTUM_WINDOW} 个交易日，无法计算动量。建议本周不调仓。")
            return "\n".join(lines)

        lines.append("排名 | 类别 | ETF | 代码 | 20日动量")
        for index, (code, momentum) in enumerate(rankings, 1):
            name = ETF_POOL.get(code, code)
            category = ETF_CATEGORIES.get(code, code)
            signal = "↑" if momentum > 0 else "↓"
            lines.append(f"  {index}  | {category} | {name} | {code} | {momentum:+.4f} {signal}")

        positive = sum(1 for _, momentum in rankings if momentum > 0)
        negative = len(rankings) - positive
        lines.append(f"\n共 {len(rankings)} 个类别代表，{positive} 个正动量，{negative} 个负动量")
        return "\n".join(lines)

    def get_portfolio_status(self) -> str:
        """查看当前持仓、现金余额和总资产。"""
        prices = self.feed.get_today_prices()
        total = self.portfolio.get_total_value(prices)
        drawdown = self.portfolio.check_drawdown(prices)
        weights = self.portfolio.get_current_weights(prices)

        lines = [f"=== 投资组合状态 ({self.feed.current_date_str}) ==="]
        lines.append(f"总资产: ￥{total:,.2f}")
        lines.append(f"现金: ￥{self.portfolio.cash:,.2f}")
        lines.append(f"当前回撤: {drawdown:.2%}")
        lines.append("")

        if not self.portfolio.positions:
            lines.append("空仓状态")
            return "\n".join(lines)

        lines.append("持仓明细:")
        lines.append("类别 | ETF | 股数 | 市值 | 权重")
        for code, shares in self.portfolio.positions.items():
            name = ETF_POOL.get(code, code)
            category = ETF_CATEGORIES.get(code, code)
            price = prices.get(code, 0.0)
            value = shares * price
            weight = weights.get(code, 0.0)
            lines.append(f"{category} | {name} | {shares} | ￥{value:,.2f} | {weight:.1%}")
        return "\n".join(lines)

    def get_recommended_allocation(self) -> str:
        """运行动量策略，获取推荐的目标配置。"""
        if not self._last_rankings:
            self._last_rankings = rank_etfs(self.feed)

        weights = generate_target_weights(self._last_rankings)
        self._last_weights = weights

        lines = [f"=== 策略推荐配置 ({self.feed.current_date_str}) ==="]
        for code, weight in sorted(weights.items(), key=lambda item: -item[1]):
            name = ETF_POOL.get(code, code)
            category = ETF_CATEGORIES.get(code, code)
            lines.append(f"  {category} / {name} ({code}): {weight:.0%}")
        return "\n".join(lines)

    def execute_rebalance(self, reasoning: str = "") -> str:
        """执行调仓，将持仓调整为策略推荐的目标配置。"""
        if not self._last_weights:
            self._last_rankings = rank_etfs(self.feed)
            self._last_weights = generate_target_weights(self._last_rankings)

        prices = self.feed.get_today_prices()
        date = self.feed.current_date_str
        orders = self.portfolio.rebalance_to(self._last_weights, prices, date)

        for order in orders:
            self.logger.log_trade(order)
        self.logger.log_decision(date, self._last_rankings, self._last_weights, reasoning)

        lines = [f"=== 调仓执行完成 ({date}) ==="]
        if orders:
            lines.append(f"共执行 {len(orders)} 笔交易:")
            for order in orders:
                name = ETF_POOL.get(order.ts_code, order.ts_code)
                lines.append(
                    f"  {order.direction} {name} {order.shares}股 @ ￥{order.price:.3f} "
                    f"金额 ￥{order.amount:,.2f} 佣金 ￥{order.commission:.2f}"
                )
        else:
            lines.append("无需调仓")

        total = self.portfolio.get_total_value(prices)
        lines.append(f"调仓后总资产: ￥{total:,.2f}")

        self._last_rankings = []
        self._last_weights = {}
        return "\n".join(lines)

    def execute_custom_rebalance(self, weights_json: str, reasoning: str = "") -> str:
        """按照你自己决定的权重执行调仓。"""
        try:
            custom_weights = json.loads(weights_json)
        except json.JSONDecodeError:
            return "错误: weights_json 不是合法的 JSON 格式"

        for code in custom_weights:
            if code not in ETF_POOL:
                return f"错误: {code} 不在 ETF 池中。可用: {', '.join(sorted(ETF_POOL.keys()))}"

        total_weight = sum(custom_weights.values())
        if abs(total_weight - 1.0) > 0.02:
            return f"错误: 权重之和为 {total_weight:.4f}，应接近 1.0"

        custom_weights = {code: weight / total_weight for code, weight in custom_weights.items()}

        prices = self.feed.get_today_prices()
        date = self.feed.current_date_str
        orders = self.portfolio.rebalance_to(custom_weights, prices, date)

        if not self._last_rankings:
            self._last_rankings = rank_etfs(self.feed)

        for order in orders:
            self.logger.log_trade(order)
        self.logger.log_decision(date, self._last_rankings, custom_weights, reasoning)

        lines = [f"=== 自定义调仓执行完成 ({date}) ==="]
        if orders:
            lines.append(f"共执行 {len(orders)} 笔交易:")
            for order in orders:
                name = ETF_POOL.get(order.ts_code, order.ts_code)
                lines.append(
                    f"  {order.direction} {name} {order.shares}股 @ ￥{order.price:.3f} "
                    f"金额 ￥{order.amount:,.2f} 佣金 ￥{order.commission:.2f}"
                )
        else:
            lines.append("无需调仓")

        total = self.portfolio.get_total_value(prices)
        lines.append(f"调仓后总资产: ￥{total:,.2f}")

        self._last_rankings = []
        self._last_weights = {}
        return "\n".join(lines)

    def get_performance_summary(self) -> str:
        """获取回测绩效指标摘要。"""
        metrics = self.tracker.get_metrics()
        if "error" in metrics:
            return metrics["error"]

        lines = ["=== 绩效摘要 ==="]
        lines.append(f"初始资金: ￥{metrics['initial_capital']:,.2f}")
        lines.append(f"最终资产: ￥{metrics['final_value']:,.2f}")
        lines.append(f"总收益率: {metrics['total_return']:+.2f}%")
        lines.append(f"年化收益: {metrics['annualized_return']:+.2f}%")
        lines.append(f"波动率: {metrics['volatility']:.2f}%")
        lines.append(f"最大回撤: {metrics['max_drawdown']:.2f}%")
        lines.append(f"最大回撤日: {metrics['max_drawdown_date']}")
        lines.append(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
        lines.append(f"卡尔玛比率: {metrics['calmar_ratio']:.2f}")
        lines.append(f"交易天数: {metrics['trading_days']}")
        return "\n".join(lines)

    def check_if_rebalance_day(self) -> str:
        """检查今天是否为调仓日（周五）。"""
        is_rebalance_day = self.feed.is_rebalance_day()
        date = self.feed.current_date_str
        return f"{'是' if is_rebalance_day else '否'}，{date} {'是' if is_rebalance_day else '不是'}调仓日"
