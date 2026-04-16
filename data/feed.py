"""模拟实时行情：逐日推进，防止未来数据泄露"""

import pandas as pd

from stock_agent.config import REBALANCE_WEEKDAY, BACKTEST_START


class MarketFeed:
    def __init__(self, all_data: dict[str, pd.DataFrame], backtest_start: str | None = None):
        self._all_data = all_data
        self._backtest_start = backtest_start or BACKTEST_START
        self._trading_dates = self._build_calendar()
        self._cursor = -1  # advance() 之后从 0 开始

    def _build_calendar(self) -> list[pd.Timestamp]:
        """合并所有 ETF 的交易日期，仅保留回测起始日之后的日期"""
        backtest_start = pd.Timestamp(self._backtest_start)
        dates = set()
        for df in self._all_data.values():
            dates.update(pd.to_datetime(df["trade_date"]).tolist())
        return sorted(d for d in dates if d >= backtest_start)

    @property
    def current_date(self) -> pd.Timestamp | None:
        if 0 <= self._cursor < len(self._trading_dates):
            return self._trading_dates[self._cursor]
        return None

    @property
    def current_date_str(self) -> str:
        d = self.current_date
        return d.strftime("%Y%m%d") if d else ""

    @property
    def total_days(self) -> int:
        return len(self._trading_dates)

    @property
    def progress(self) -> int:
        return self._cursor + 1

    def advance(self) -> bool:
        """推进到下一个交易日，返回 False 表示数据结束"""
        self._cursor += 1
        return self._cursor < len(self._trading_dates)

    def get_history(self, ts_code: str, lookback: int) -> pd.DataFrame:
        """返回截至当前日期的最近 lookback 个交易日数据（无未来数据泄露）"""
        if self.current_date is None:
            return pd.DataFrame()
        df = self._all_data.get(ts_code)
        if df is None:
            return pd.DataFrame()
        mask = pd.to_datetime(df["trade_date"]) <= self.current_date
        return df[mask].tail(lookback).copy()

    def get_today_prices(self) -> dict[str, float]:
        """返回当日各 ETF 的收盘价 {ts_code: close}"""
        if self.current_date is None:
            return {}
        prices = {}
        for ts_code, df in self._all_data.items():
            row = df[pd.to_datetime(df["trade_date"]) == self.current_date]
            if not row.empty:
                prices[ts_code] = float(row.iloc[0]["close"])
        return prices

    def is_rebalance_day(self) -> bool:
        """判断当前是否为调仓日（周五）"""
        d = self.current_date
        if d is None:
            return False
        return d.weekday() == REBALANCE_WEEKDAY

    def reset(self):
        self._cursor = -1
