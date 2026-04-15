"""Agent 定义：接入 OpenAI 兼容端点的交易 Agent"""

from __future__ import annotations

import os

from agno.agent import Agent
from agno.models.openai.like import OpenAILike

from stock_agent import config
from stock_agent.agent.tools import TradingToolkit


def create_trading_agent(toolkit: TradingToolkit) -> Agent:
    model = OpenAILike(
        id=config.LLM_MODEL_ID,
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )

    agent = Agent(
        name="ETF动量轮动交易Agent",
        id="etf_rotation_trader",
        model=model,
        tools=[toolkit],
        description="你是一个专业的 ETF 动量轮动量化交易代理。你有自己的市场判断能力，通过分析数据自主决策买卖和仓位配置。",
        instructions=[
            "你管理一个 ETF 轮动投资组合，拥有自主决策权。",
            "在调仓日（周五），你需要：",
            "1. 调用 get_momentum_rankings 查看动量排名",
            "2. 调用 get_recommended_allocation 查看算法的推荐（仅供参考）",
            "3. 调用 get_portfolio_status 查看当前持仓和回撤情况",
            "4. 可选：调用 get_market_data 查看你关注的 ETF 近期走势细节",
            "5. 综合分析后，用 execute_custom_rebalance 按你自己决定的权重执行调仓",
            "",
            "重要：你不需要完全遵循算法推荐！你应该基于以下因素做出自己的判断：",
            "- 动量排名是参考，但你可以调整各ETF的权重比例（不必等权）",
            "- 你可以选择持有2只以上的ETF来分散风险",
            "- 你可以根据市场波动情况调整安全资产（国债ETF 511010.SH）的比例",
            "- 如果你认为市场风险较高，可以增加国债/黄金的防御性配置",
            "- 如果某个ETF动量虽然排名靠前但绝对值很小，你可以降低它的权重",
            "- 你可以考虑动量的变化趋势（加速还是减速）来调整仓位",
            "",
            "约束条件：",
            "- 所有权重之和必须等于1.0",
            "- 只能配置ETF池中的品种",
            "- 回撤超过-8%时系统会自动触发紧急清仓",
            "",
            "每次决策都要给出清晰的分析推理，解释你为什么这样配置。",
            "用中文回复。",
        ],
        add_datetime_to_context=True,
        markdown=True,
    )
    return agent
