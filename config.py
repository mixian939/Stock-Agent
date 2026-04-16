"""stock_agent 集中配置"""

from __future__ import annotations

import os
from pathlib import Path

# --- 项目根目录 ---
BASE_DIR = Path(__file__).resolve().parent

# --- Tushare ---
TUSHARE_TOKEN = "b4926c0f0e4c96af9cf8073e380f9c734f59e5b1072a228f602a04be"

# --- 聚宽（备选数据源） ---
JQ_ACCOUNT = "15823061718"
JQ_PASSWORD = "168168yYjw"

# --- 主 Agent / OpenAI 兼容接口 ---
LLM_BASE_URL = "https://api.ikuncode.cc/v1"
LLM_MODEL_ID = "gpt-5.4"
LLM_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "sk-SvWtv3ejIhWBKm489HAHQEHlOavIdIQescTVRyEUYDEnzVlk",
)

# --- 本地 LM Studio 金融子 Agent ---
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
LM_STUDIO_MODEL_ID = os.getenv("LM_STUDIO_MODEL_ID", "fin-r1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "sk-lm-vjQeAz3R:ynyBRX4fNUWgGllzbpCE")
LM_STUDIO_TIMEOUT_SECONDS = float(os.getenv("LM_STUDIO_TIMEOUT_SECONDS", "90"))

# --- 双 Agent 决策权重 ---
SUB_AGENT_WEIGHT = 0.60
MAIN_AGENT_WEIGHT = 0.40

# --- ETF 池 ---
# 说明：
# 1. ETF 数量扩充为每个资产类别配置多个候选 ETF；
# 2. 策略层会先在每个类别中选出 1 只代表 ETF，再在 7 个类别之间做轮动；
# 3. 这样既扩大了 ETF 池，又保持了资产类别仍然只有 7 类。
ETF_UNIVERSE: dict[str, dict[str, str]] = {
    "510300.SH": {"name": "沪深300ETF华泰柏瑞", "category": "沪深300"},
    "159919.SZ": {"name": "沪深300ETF嘉实", "category": "沪深300"},
    "510500.SH": {"name": "中证500ETF南方", "category": "中证500"},
    "159922.SZ": {"name": "中证500ETF嘉实", "category": "中证500"},
    "159915.SZ": {"name": "创业板ETF易方达", "category": "创业板"},
    "159949.SZ": {"name": "创业板50ETF华安", "category": "创业板"},
    "510880.SH": {"name": "红利ETF华泰柏瑞", "category": "红利"},
    "515180.SH": {"name": "红利ETF易方达", "category": "红利"},
    "511010.SH": {"name": "国债ETF国泰", "category": "国债"},
    "511260.SH": {"name": "十年国债ETF国泰", "category": "国债"},
    "518880.SH": {"name": "黄金ETF华安", "category": "黄金"},
    "159934.SZ": {"name": "黄金ETF易方达", "category": "黄金"},
    "513100.SH": {"name": "纳指100ETF国泰", "category": "纳指100"},
    "159941.SZ": {"name": "纳指ETF广发", "category": "纳指100"},
}

ETF_POOL = {code: meta["name"] for code, meta in ETF_UNIVERSE.items()}
ETF_CATEGORIES = {code: meta["category"] for code, meta in ETF_UNIVERSE.items()}
ETF_CATEGORY_ORDER = [
    "沪深300",
    "中证500",
    "创业板",
    "红利",
    "国债",
    "黄金",
    "纳指100",
]

SAFE_ASSET = "511010.SH"
SAFE_ASSET_CATEGORY = "国债"

# Tushare -> 聚宽 代码映射
TUSHARE_TO_JQ = {
    "510300.SH": "510300.XSHG",
    "159919.SZ": "159919.XSHE",
    "510500.SH": "510500.XSHG",
    "159922.SZ": "159922.XSHE",
    "159915.SZ": "159915.XSHE",
    "159949.SZ": "159949.XSHE",
    "510880.SH": "510880.XSHG",
    "515180.SH": "515180.XSHG",
    "511010.SH": "511010.XSHG",
    "511260.SH": "511260.XSHG",
    "518880.SH": "518880.XSHG",
    "159934.SZ": "159934.XSHE",
    "513100.SH": "513100.XSHG",
    "159941.SZ": "159941.XSHE",
}

# --- 策略参数 ---
MOMENTUM_WINDOW = 20        # 动量计算窗口（交易日）
TOP_N = 2                   # 选择动量前 N 个类别代表
REBALANCE_WEEKDAY = 4       # 周五 (0=周一)
MAX_SINGLE_WEIGHT = 0.50    # 单只 ETF 最大仓位
MAX_DRAWDOWN_STOP = -0.08   # 最大回撤止损线
STOP_COOLDOWN_DAYS = 10     # 止损后冷却期（交易日）
COMMISSION_RATE = 0.0003    # 手续费率 0.03%
LOT_SIZE = 100              # A 股最小交易单位

# --- 回测参数 ---
INITIAL_CAPITAL = 1_000_000.0
DATA_START = "20241101"         # 提前准备动量窗口所需数据
BACKTEST_START = "20250101"     # 回测实际起始日
DATA_END = "20250630"

# --- 路径 ---
DATA_CACHE_DIR = BASE_DIR / "data" / "cache"
LOG_DIR = BASE_DIR / "logs"
