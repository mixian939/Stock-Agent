"""数据获取层：Tushare 优先，聚宽备选，本地 CSV 缓存"""

import time
from pathlib import Path

import pandas as pd

from stock_agent.config import (
    TUSHARE_TOKEN,
    JQ_ACCOUNT,
    JQ_PASSWORD,
    ETF_POOL,
    TUSHARE_TO_JQ,
    DATA_CACHE_DIR,
    DATA_START,
    DATA_END,
)


class DataFetcher:
    def __init__(
        self,
        cache_dir: Path = DATA_CACHE_DIR,
        start: str = DATA_START,
        end: str = DATA_END,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.start = start
        self.end = end
        self._source = None  # 记录实际使用的数据源

    # ---- 公开接口 ----

    def fetch_etf(self, ts_code: str) -> pd.DataFrame:
        """获取单只 ETF 日线数据，优先读缓存"""
        cache_file = self._cache_path(ts_code)
        if cache_file.exists():
            df = pd.read_csv(cache_file, parse_dates=["trade_date"])
            return df

        # 尝试 Tushare → 聚宽
        df = self._try_tushare(ts_code)
        if df is None or df.empty:
            df = self._try_joinquant(ts_code)
        if df is None or df.empty:
            print(f"[DataFetcher] ⚠ 无法获取 {ts_code} 的数据，Tushare 和聚宽均失败")
            return pd.DataFrame()

        df = self._normalize(df, ts_code)
        df.to_csv(cache_file, index=False)
        return df

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """获取 ETF 池中所有 ETF 的数据"""
        result = {}
        failed = []
        for ts_code in ETF_POOL:
            print(f"[DataFetcher] 获取 {ts_code} ({ETF_POOL[ts_code]}) ...")
            df = self.fetch_etf(ts_code)
            if df.empty:
                failed.append(ts_code)
            else:
                result[ts_code] = df
            time.sleep(0.3)  # 避免触发频率限制
        if failed:
            print(f"[DataFetcher] ⚠ 以下 ETF 数据获取失败，将跳过: {failed}")
        print(f"[DataFetcher] 获取完成 ({len(result)}/{len(ETF_POOL)})，数据源: {self._source}")
        return result

    @property
    def source(self) -> str | None:
        return self._source

    # ---- Tushare ----

    def _try_tushare(self, ts_code: str) -> pd.DataFrame | None:
        try:
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            pro = ts.pro_api()

            # 优先 fund_daily
            try:
                df = pro.fund_daily(
                    ts_code=ts_code,
                    start_date=self.start,
                    end_date=self.end,
                )
                if df is not None and not df.empty:
                    self._source = "tushare/fund_daily"
                    return df
            except Exception:
                pass

            # 备选 pro_bar
            try:
                df = ts.pro_bar(
                    ts_code=ts_code,
                    asset="E",
                    adj="qfq",
                    start_date=self.start,
                    end_date=self.end,
                )
                if df is not None and not df.empty:
                    self._source = "tushare/pro_bar"
                    return df
            except Exception:
                pass

        except Exception as e:
            print(f"[DataFetcher] Tushare 失败: {e}")
        return None

    # ---- 聚宽 ----

    def _try_joinquant(self, ts_code: str) -> pd.DataFrame | None:
        try:
            import jqdatasdk as jq
            jq.auth(JQ_ACCOUNT, JQ_PASSWORD)

            jq_code = TUSHARE_TO_JQ.get(ts_code)
            if not jq_code:
                return None

            start_dt = f"{self.start[:4]}-{self.start[4:6]}-{self.start[6:]}"
            end_dt = f"{self.end[:4]}-{self.end[4:6]}-{self.end[6:]}"

            df = jq.get_price(
                jq_code,
                start_date=start_dt,
                end_date=end_dt,
                frequency="daily",
                fields=["open", "high", "low", "close", "volume", "money"],
                skip_paused=True,
                fq="pre",
            )
            if df is not None and not df.empty:
                self._source = "joinquant"
                # 转换为统一格式
                df = df.reset_index()
                df = df.rename(columns={
                    "index": "trade_date",
                    "volume": "vol",
                    "money": "amount",
                })
                df["ts_code"] = ts_code
                # 计算涨跌幅
                df["pre_close"] = df["close"].shift(1)
                df["change"] = df["close"] - df["pre_close"]
                df["pct_chg"] = (df["change"] / df["pre_close"] * 100).round(4)
                return df
        except Exception as e:
            print(f"[DataFetcher] 聚宽失败: {e}")
        return None

    # ---- 数据标准化 ----

    def _normalize(self, df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
        """统一列名和排序"""
        required = ["ts_code", "trade_date", "open", "high", "low", "close"]
        if "ts_code" not in df.columns:
            df["ts_code"] = ts_code
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").reset_index(drop=True)

        # 确保必要列存在
        for col in required:
            if col not in df.columns:
                raise ValueError(f"数据缺少必要列: {col}")

        # 补充可选列
        if "pct_chg" not in df.columns and "pre_close" in df.columns:
            df["pct_chg"] = ((df["close"] - df["pre_close"]) / df["pre_close"] * 100).round(4)

        return df

    def _cache_path(self, ts_code: str) -> Path:
        safe_code = ts_code.replace(".", "_")
        return self.cache_dir / f"{safe_code}_{self.start}_{self.end}.csv"
