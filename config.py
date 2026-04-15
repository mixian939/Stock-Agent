"""stock_agent 集中配置"""

import os
from pathlib import Path

# --- 项目根目录 ---
BASE_DIR = Path(__file__).resolve().parent

# --- Tushare ---
TUSHARE_TOKEN = "b4926c0f0e4c96af9cf8073e380f9c734f59e5b1072a228f602a04be"

# --- 聚宽 (备选数据源) ---
JQ_ACCOUNT = "15823061718"
JQ_PASSWORD = "168168yYjw"

# --- LLM ---
LLM_BASE_URL = "https://api.ikuncode.cc/v1"
LLM_MODEL_ID = "gpt-5.3-codex"
LLM_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "sk-SvWtv3ejIhWBKm489HAHQEHlOavIdIQescTVRyEUYDEnzVlk",
)

# --- ETF 池 ---
ETF_POOL = {
    "510300.SH": "沪深300ETF",
    "510500.SH": "中证500ETF",
    "159915.SZ": "创业板ETF",
    "510880.SH": "红利ETF",
    "511010.SH": "国债ETF",
    "518880.SH": "黄金ETF",
    "513100.SH": "纳指100ETF",
}
SAFE_ASSET = "511010.SH"

# Tushare -> 聚宽 代码映射
TUSHARE_TO_JQ = {
    "510300.SH": "510300.XSHG",
    "510500.SH": "510500.XSHG",
    "159915.SZ": "159915.XSHE",
    "510880.SH": "510880.XSHG",
    "511010.SH": "511010.XSHG",
    "518880.SH": "518880.XSHG",
    "513100.SH": "513100.XSHG",
}

# --- 策略参数 ---
MOMENTUM_WINDOW = 20        # 动量计算窗口（交易日）
TOP_N = 2                   # 选择动量前 N 名
REBALANCE_WEEKDAY = 4       # 周五 (0=周一)
MAX_SINGLE_WEIGHT = 0.50    # 单只 ETF 最大仓位
MAX_DRAWDOWN_STOP = -0.08   # 最大回撤止损线
STOP_COOLDOWN_DAYS = 10     # 止损后冷却期（交易日）
COMMISSION_RATE = 0.0003    # 手续费率 0.03%
LOT_SIZE = 100              # A 股最小交易单位

# --- 回测参数 ---
INITIAL_CAPITAL = 1_000_000.0
DATA_START = "20241101"         # 数据获取起始日（提前获取，保证回测首日即可计算动量）
BACKTEST_START = "20250101"     # 回测实际起始日
DATA_END = "20250630"

# --- 路径 ---
DATA_CACHE_DIR = BASE_DIR / "data" / "cache"
LOG_DIR = BASE_DIR / "logs"
