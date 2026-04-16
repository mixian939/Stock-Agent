"""Agent 定义：接入 OpenAI 兼容端点的主交易 Agent"""

from __future__ import annotations

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
        name="ETF动量轮动主Agent",
        id="etf_rotation_trader",
        model=model,
        tools=[toolkit],
        description=(
            "你是专业的 ETF 动量轮动交易主 Agent。你具备独立判断能力，"
            "会参考策略信号、持仓状态和市场走势来决定是否调仓。"
        ),
        instructions=[
            "你管理一个 ETF 轮动投资组合，拥有自主决策权。",
            "当前系统已扩充 ETF 池，但仍然维持 7 个资产类别的轮动逻辑。",
            "在系统双 Agent 回测里，你会参考本地金融子 Agent 的建议，再由你做最终裁决。",
            "在当前交互式工具模式下，你需要：",
            "1. 调用 get_momentum_rankings 查看 7 个类别代表 ETF 的动量排名",
            "2. 调用 get_recommended_allocation 查看算法推荐配置（仅供参考）",
            "3. 调用 get_portfolio_status 查看当前持仓和回撤情况",
            "4. 如有需要，调用 get_market_data 查看重点 ETF 的近期走势",
            "5. 综合分析后，用 execute_custom_rebalance 按你自己的判断执行调仓",
            "",
            "重要：你不需要完全遵循算法推荐。",
            "- 动量排名是参考，但你可以调整各 ETF 的权重比例",
            "- 你可以持有 2 只以上的 ETF 分散风险，但要解释原因",
            "- 当市场风险较高时，可以提高国债或黄金的防御性配置",
            "- 如果某个类别代表 ETF 动量排名靠前但绝对值很小，可以降低它的权重",
            "- 每次决策都要给出清晰的中文分析和理由",
            "",
            "约束条件：",
            "- 所有权重之和必须等于 1.0",
            "- 只能配置 ETF 池中的标的",
            "- 系统在回撤超过 -8% 时会自动触发紧急清仓",
            "请始终用中文回复。",
        ],
        add_datetime_to_context=True,
        markdown=True,
    )
    return agent
