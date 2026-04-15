"""CLI 入口

Usage:
    python -m stock_agent.run_backtest              # agent 模式
    python -m stock_agent.run_backtest --headless    # 纯策略模式（无 LLM）
"""

import argparse
import sys

from stock_agent.backtest.simulator import BacktestSimulator


def main():
    parser = argparse.ArgumentParser(description="ETF 动量轮动回测")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="纯策略模式，不调用 LLM",
    )
    args = parser.parse_args()

    sim = BacktestSimulator()

    if args.headless:
        print("运行模式: Headless（纯策略）")
        metrics = sim.run_headless()
    else:
        print("运行模式: Agent（LLM 决策）")
        metrics = sim.run_agent()

    return 0 if metrics.get("final_value", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
