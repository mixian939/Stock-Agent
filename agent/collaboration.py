"""双 Agent 协调层：LM Studio 金融子 Agent + 主 Agent 加权裁决"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from openai import OpenAI

from stock_agent.config import (
    ETF_POOL,
    ETF_CATEGORIES,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL_ID,
    LM_STUDIO_API_KEY,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_MODEL_ID,
    LM_STUDIO_TIMEOUT_SECONDS,
    MAIN_AGENT_WEIGHT,
    MAX_SINGLE_WEIGHT,
    SAFE_ASSET,
    SUB_AGENT_WEIGHT,
    TOP_N,
)
from stock_agent.engine.portfolio import Order, Portfolio
from stock_agent.logging_.logger import TradingLogger
from stock_agent.strategy.momentum import generate_target_weights, rank_etfs, resolve_safe_asset
from stock_agent.data.feed import MarketFeed


@dataclass
class AgentAdvice:
    agent_name: str
    model_id: str
    source: str
    should_rebalance: bool
    weights: dict[str, float]
    scores: dict[str, float]
    summary: str
    reasoning: str
    raw_content: str = ""


@dataclass
class CoordinatedDecision:
    date: str
    target_weights: dict[str, float]
    should_rebalance: bool
    execution_status: str
    orders: list[Order]
    summary: str
    reasoning: str
    sub_agent: AgentAdvice
    main_agent: AgentAdvice
    weighted_scores: dict[str, float]
    algorithm_recommended_weights: dict[str, float]
    current_weights_before: dict[str, float]


def combine_scores(
    sub_scores: dict[str, float],
    main_scores: dict[str, float],
    sub_weight: float = SUB_AGENT_WEIGHT,
    main_weight: float = MAIN_AGENT_WEIGHT,
) -> dict[str, float]:
    """按 60/40 权重合并双 Agent 评分。"""
    all_codes = sorted(set(sub_scores) | set(main_scores))
    combined: dict[str, float] = {}
    for code in all_codes:
        sub_score = float(sub_scores.get(code, 0))
        main_score = float(main_scores.get(code, 0))
        combined[code] = round(sub_score * sub_weight + main_score * main_weight, 2)
    return combined


def score_weighted_allocation(
    scores: dict[str, float],
    safe_asset: str,
    top_n: int = TOP_N,
    max_single_weight: float = MAX_SINGLE_WEIGHT,
) -> dict[str, float]:
    """在主 Agent 输出非法权重时，使用加权评分退化生成配置。"""
    candidates = [
        (code, score)
        for code, score in scores.items()
        if code != safe_asset and score >= 55
    ]
    candidates.sort(key=lambda item: item[1], reverse=True)
    selected = candidates[:top_n]

    if not selected:
        return {safe_asset: 1.0}

    total_score = sum(score for _, score in selected)
    if total_score <= 0:
        return {safe_asset: 1.0}

    weights = {code: score / total_score for code, score in selected}
    for code in list(weights.keys()):
        if weights[code] > max_single_weight:
            excess = weights[code] - max_single_weight
            weights[code] = max_single_weight
            weights[safe_asset] = weights.get(safe_asset, 0.0) + excess

    weight_sum = sum(weights.values())
    return {code: round(weight / weight_sum, 4) for code, weight in weights.items()}


def normalize_weights(
    allowed_codes: list[str],
    raw_weights: dict[str, float],
    safe_asset: str,
    fallback_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """清洗并归一化权重，限制在允许交易的 ETF 范围内。"""
    cleaned: dict[str, float] = {}
    for code, value in raw_weights.items():
        if code not in allowed_codes:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            cleaned[code] = numeric

    if not cleaned:
        cleaned = dict(fallback_weights or {safe_asset: 1.0})

    total = sum(cleaned.values())
    if total <= 0:
        cleaned = dict(fallback_weights or {safe_asset: 1.0})
        total = sum(cleaned.values())

    normalized = {code: value / total for code, value in cleaned.items()}
    for code in list(normalized.keys()):
        if code != safe_asset and normalized[code] > MAX_SINGLE_WEIGHT:
            excess = normalized[code] - MAX_SINGLE_WEIGHT
            normalized[code] = MAX_SINGLE_WEIGHT
            normalized[safe_asset] = normalized.get(safe_asset, 0.0) + excess

    total = sum(normalized.values())
    return {code: round(value / total, 4) for code, value in normalized.items() if value > 0}


class DualAgentCoordinator:
    def __init__(
        self,
        feed: MarketFeed,
        portfolio: Portfolio,
        logger: TradingLogger,
    ):
        self.feed = feed
        self.portfolio = portfolio
        self.logger = logger

    def run_rebalance_cycle(self) -> CoordinatedDecision:
        snapshot = self._build_snapshot()
        sub_agent = self._get_sub_agent_advice(snapshot)
        main_agent = self._get_main_agent_decision(snapshot, sub_agent)

        weighted_scores = combine_scores(sub_agent.scores, main_agent.scores)
        fallback_weights = score_weighted_allocation(
            weighted_scores,
            safe_asset=snapshot["safe_asset"],
        )
        target_weights = normalize_weights(
            allowed_codes=snapshot["eligible_codes"],
            raw_weights=main_agent.weights,
            safe_asset=snapshot["safe_asset"],
            fallback_weights=fallback_weights,
        )

        reasoning = self._compose_reasoning(
            snapshot=snapshot,
            sub_agent=sub_agent,
            main_agent=main_agent,
            weighted_scores=weighted_scores,
            target_weights=target_weights,
        )

        orders: list[Order] = []
        execution_status = "hold"
        if main_agent.should_rebalance:
            prices = self.feed.get_today_prices()
            orders = self.portfolio.rebalance_to(target_weights, prices, snapshot["date"])
            execution_status = "executed" if orders else "no_trade"
            for order in orders:
                self.logger.log_trade(order)

        self.logger.log_decision(
            snapshot["date"],
            snapshot["rankings"],
            target_weights,
            reasoning,
            extra={
                "decision_mode": "dual_agent_weighted",
                "execution_status": execution_status,
                "should_rebalance": main_agent.should_rebalance,
                "score_weights": {
                    "sub_agent": SUB_AGENT_WEIGHT,
                    "main_agent": MAIN_AGENT_WEIGHT,
                },
                "algorithm_recommended_weights": snapshot["recommended_weights"],
                "current_weights_before": snapshot["current_weights"],
                "sub_agent": asdict(sub_agent),
                "main_agent": asdict(main_agent),
                "weighted_scores": weighted_scores,
            },
        )

        return CoordinatedDecision(
            date=snapshot["date"],
            target_weights=target_weights,
            should_rebalance=main_agent.should_rebalance,
            execution_status=execution_status,
            orders=orders,
            summary=main_agent.summary,
            reasoning=reasoning,
            sub_agent=sub_agent,
            main_agent=main_agent,
            weighted_scores=weighted_scores,
            algorithm_recommended_weights=snapshot["recommended_weights"],
            current_weights_before=snapshot["current_weights"],
        )

    def _build_snapshot(self) -> dict:
        rankings = rank_etfs(self.feed)
        recommended_weights = generate_target_weights(rankings)
        safe_asset = resolve_safe_asset(rankings, default_safe_asset=SAFE_ASSET)
        prices = self.feed.get_today_prices()
        current_weights = self.portfolio.get_current_weights(prices)

        position_details = []
        for code, shares in self.portfolio.positions.items():
            position_details.append(
                {
                    "ts_code": code,
                    "name": ETF_POOL.get(code, code),
                    "category": ETF_CATEGORIES.get(code, code),
                    "shares": shares,
                    "price": round(prices.get(code, 0.0), 4),
                    "weight": round(current_weights.get(code, 0.0), 4),
                }
            )

        market_windows = {}
        for code, _ in rankings[: min(5, len(rankings))]:
            hist = self.feed.get_history(code, lookback=5)
            market_windows[code] = [
                {
                    "date": row["trade_date"].strftime("%Y-%m-%d") if hasattr(row["trade_date"], "strftime") else str(row["trade_date"]),
                    "close": round(float(row["close"]), 4),
                    "pct_chg": round(float(row.get("pct_chg", 0.0)), 4),
                }
                for _, row in hist.iterrows()
            ]

        return {
            "date": self.feed.current_date_str,
            "rankings": rankings,
            "rankings_payload": [
                {
                    "ts_code": code,
                    "name": ETF_POOL.get(code, code),
                    "category": ETF_CATEGORIES.get(code, code),
                    "momentum": round(momentum, 4),
                }
                for code, momentum in rankings
            ],
            "recommended_weights": recommended_weights,
            "current_weights": current_weights,
            "positions": position_details,
            "safe_asset": safe_asset,
            "eligible_codes": [code for code, _ in rankings],
            "market_windows": market_windows,
        }

    def _get_sub_agent_advice(self, snapshot: dict) -> AgentAdvice:
        prompt = (
            "你是本地 LM Studio 运行的金融领域子 Agent，只负责给主 Agent 提供调仓建议，"
            "不能执行交易。请严格基于输入数据输出 JSON，不要输出 Markdown。\n"
            "请返回字段：should_rebalance、weights、scores、summary、reasoning。\n"
            "scores 是对当前 7 个类别代表 ETF 的 0-100 打分，weights 为你的建议仓位。"
        )
        try:
            content = self._call_model(
                base_url=LM_STUDIO_BASE_URL,
                api_key=LM_STUDIO_API_KEY,
                model_id=LM_STUDIO_MODEL_ID,
                system_prompt=prompt,
                user_payload={
                    "task": "请基于市场快照给出金融子 Agent 建议。",
                    "market_snapshot": snapshot,
                },
                timeout=LM_STUDIO_TIMEOUT_SECONDS,
            )
            data = self._parse_json(content)
            return AgentAdvice(
                agent_name="financial_sub_agent",
                model_id=LM_STUDIO_MODEL_ID,
                source="lm_studio",
                should_rebalance=bool(data.get("should_rebalance", True)),
                weights=normalize_weights(
                    allowed_codes=snapshot["eligible_codes"],
                    raw_weights=data.get("weights", {}),
                    safe_asset=snapshot["safe_asset"],
                    fallback_weights=snapshot["recommended_weights"],
                ),
                scores=self._normalize_scores(
                    snapshot["eligible_codes"],
                    data.get("scores", {}),
                    snapshot,
                ),
                summary=str(data.get("summary", "")).strip() or "子 Agent 提供了调仓建议。",
                reasoning=str(data.get("reasoning", "")).strip() or "未提供详细理由。",
                raw_content=content,
            )
        except Exception as exc:
            return self._fallback_sub_agent(snapshot, error_message=str(exc))

    def _get_main_agent_decision(self, snapshot: dict, sub_agent: AgentAdvice) -> AgentAdvice:
        prompt = (
            "你是主交易 Agent（gpt-5.4），负责最终调仓裁决。\n"
            "你必须先给出你自己的 0-100 打分，再结合金融子 Agent 的评分按固定权重计算："
            f"子 Agent {SUB_AGENT_WEIGHT:.0%}，主 Agent {MAIN_AGENT_WEIGHT:.0%}。\n"
            "然后根据加权评分和你的判断，决定是否调仓、调哪些 ETF、各自多少仓位。\n"
            "请严格输出 JSON，不要输出 Markdown。\n"
            "返回字段：should_rebalance、weights、scores、summary、reasoning。"
        )
        try:
            content = self._call_model(
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
                model_id=LLM_MODEL_ID,
                system_prompt=prompt,
                user_payload={
                    "task": "请根据市场快照和金融子 Agent 建议做最终裁决。",
                    "market_snapshot": snapshot,
                    "sub_agent": asdict(sub_agent),
                },
            )
            data = self._parse_json(content)
            return AgentAdvice(
                agent_name="primary_agent",
                model_id=LLM_MODEL_ID,
                source="primary_llm",
                should_rebalance=bool(data.get("should_rebalance", True)),
                weights=normalize_weights(
                    allowed_codes=snapshot["eligible_codes"],
                    raw_weights=data.get("weights", {}),
                    safe_asset=snapshot["safe_asset"],
                    fallback_weights=sub_agent.weights or snapshot["recommended_weights"],
                ),
                scores=self._normalize_scores(
                    snapshot["eligible_codes"],
                    data.get("scores", {}),
                    snapshot,
                ),
                summary=str(data.get("summary", "")).strip() or "主 Agent 已完成最终裁决。",
                reasoning=str(data.get("reasoning", "")).strip() or "未提供详细理由。",
                raw_content=content,
            )
        except Exception as exc:
            return self._fallback_main_agent(snapshot, sub_agent, error_message=str(exc))

    def _fallback_sub_agent(self, snapshot: dict, error_message: str) -> AgentAdvice:
        scores = self._heuristic_scores(snapshot)
        weights = score_weighted_allocation(scores, safe_asset=snapshot["safe_asset"])
        return AgentAdvice(
            agent_name="financial_sub_agent",
            model_id=LM_STUDIO_MODEL_ID,
            source="fallback",
            should_rebalance=True,
            weights=weights,
            scores=scores,
            summary="LM Studio 不可用，子 Agent 已退化为动量启发式建议。",
            reasoning=(
                "本地金融模型调用失败，已使用类别代表 ETF 的动量和安全资产偏好生成建议。"
                f"错误信息: {error_message}"
            ),
        )

    def _fallback_main_agent(
        self,
        snapshot: dict,
        sub_agent: AgentAdvice,
        error_message: str,
    ) -> AgentAdvice:
        recommended = snapshot["recommended_weights"]
        scores = self._heuristic_scores(snapshot)
        for code, weight in recommended.items():
            scores[code] = min(100.0, scores.get(code, 0.0) + weight * 20)
        combined = combine_scores(sub_agent.scores, scores)
        weights = score_weighted_allocation(combined, safe_asset=snapshot["safe_asset"])
        return AgentAdvice(
            agent_name="primary_agent",
            model_id=LLM_MODEL_ID,
            source="fallback",
            should_rebalance=True,
            weights=weights,
            scores=scores,
            summary="主 Agent 模型调用失败，已退化为规则化裁决。",
            reasoning=(
                "主 Agent LLM 不可用，已结合算法推荐、子 Agent 建议和加权评分生成最终仓位。"
                f"错误信息: {error_message}"
            ),
        )

    def _heuristic_scores(self, snapshot: dict) -> dict[str, float]:
        scores: dict[str, float] = {}
        rankings = {code: momentum for code, momentum in snapshot["rankings"]}
        for code in snapshot["eligible_codes"]:
            momentum = rankings.get(code, 0.0)
            score = 50.0 + momentum * 400.0
            if code == snapshot["safe_asset"]:
                score += 5.0
            scores[code] = round(max(0.0, min(100.0, score)), 2)
        return scores

    def _normalize_scores(
        self,
        allowed_codes: list[str],
        raw_scores: dict[str, float],
        snapshot: dict,
    ) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for code in allowed_codes:
            try:
                value = float(raw_scores.get(code, 0))
            except (TypeError, ValueError):
                value = 0.0
            normalized[code] = round(max(0.0, min(100.0, value)), 2)

        if any(value > 0 for value in normalized.values()):
            return normalized
        return self._heuristic_scores(snapshot)

    def _compose_reasoning(
        self,
        snapshot: dict,
        sub_agent: AgentAdvice,
        main_agent: AgentAdvice,
        weighted_scores: dict[str, float],
        target_weights: dict[str, float],
    ) -> str:
        top_weighted = sorted(weighted_scores.items(), key=lambda item: item[1], reverse=True)
        weighted_text = ", ".join(
            f"{ETF_POOL.get(code, code)} {score:.1f}"
            for code, score in top_weighted[: min(3, len(top_weighted))]
        )
        target_text = ", ".join(
            f"{ETF_POOL.get(code, code)} {weight:.0%}"
            for code, weight in sorted(target_weights.items(), key=lambda item: item[1], reverse=True)
        )
        return (
            f"子 Agent 摘要：{sub_agent.summary}\n"
            f"主 Agent 摘要：{main_agent.summary}\n"
            f"主 Agent 按 60/40 权重整合双 Agent 评分后，最高分组合为：{weighted_text}。\n"
            f"算法参考配置：{self._format_weights(snapshot['recommended_weights'])}。\n"
            f"最终目标配置：{target_text}。\n"
            f"子 Agent 理由：{sub_agent.reasoning}\n"
            f"主 Agent 理由：{main_agent.reasoning}"
        )

    def _format_weights(self, weights: dict[str, float]) -> str:
        return ", ".join(
            f"{ETF_POOL.get(code, code)} {weight:.0%}"
            for code, weight in sorted(weights.items(), key=lambda item: item[1], reverse=True)
        )

    def _call_model(
        self,
        base_url: str,
        api_key: str,
        model_id: str,
        system_prompt: str,
        user_payload: dict,
        timeout: float | None = None,
    ) -> str:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        response = client.chat.completions.create(
            model=model_id,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
            ],
        )
        message = response.choices[0].message if response.choices else None
        content = message.content if message else ""
        if not content:
            raise ValueError("模型未返回内容")
        return content

    def _parse_json(self, content: str) -> dict:
        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("模型返回内容不是合法 JSON")
            return json.loads(text[start : end + 1])
