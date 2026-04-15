"""策略对比 REST API：算法 vs AI 回测结果对比"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from stock_agent.server.state import get_state, get_dual_state
from stock_agent.config import ETF_POOL

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("/status")
def compare_status():
    """对比状态：headless 是否就绪、agent 回测进度"""
    dual = get_dual_state()
    return {
        "headless_ready": dual.headless is not None,
        "agent_status": dual.agent_status,
        "agent_error": dual.agent_error,
    }


@router.get("/nav")
def compare_nav():
    """按日期对齐的净值 + 回撤对比数据"""
    dual = get_dual_state()
    if dual.headless is None:
        raise HTTPException(503, "回测尚未完成")

    # 以 headless 为基准构建日期索引
    algo_by_date = {r["date"]: r for r in dual.headless.tracker.nav_history}

    ai_by_date = {}
    if dual.agent is not None:
        ai_by_date = {r["date"]: r for r in dual.agent.tracker.nav_history}

    result = []
    for date in sorted(algo_by_date.keys()):
        algo = algo_by_date[date]
        point = {
            "date": date,
            "algo_nav": algo["nav"],
            "algo_drawdown": algo["drawdown"],
        }
        if date in ai_by_date:
            ai = ai_by_date[date]
            point["ai_nav"] = ai["nav"]
            point["ai_drawdown"] = ai["drawdown"]
        result.append(point)

    return result


@router.get("/metrics")
def compare_metrics():
    """双模式绩效指标对比"""
    dual = get_dual_state()
    if dual.headless is None:
        raise HTTPException(503, "回测尚未完成")

    algo_metrics = dual.headless.tracker.get_metrics()
    algo_metrics["total_trades"] = len(dual.headless.portfolio.order_history)

    ai_metrics = None
    if dual.agent is not None:
        ai_metrics = dual.agent.tracker.get_metrics()
        ai_metrics["total_trades"] = len(dual.agent.portfolio.order_history)

    return {"algo": algo_metrics, "ai": ai_metrics}


@router.get("/decisions")
def compare_decisions():
    """调仓决策对比：逐日对齐算法 vs AI 的决策和理由"""
    dual = get_dual_state()
    if dual.headless is None:
        raise HTTPException(503, "回测尚未完成")

    # 按日期索引决策（跳过 EMERGENCY_LIQUIDATION 类型）
    algo_decisions = {}
    for d in dual.headless.logger.decision_log:
        if d.get("type") == "EMERGENCY_LIQUIDATION":
            continue
        algo_decisions[d["date"]] = d

    ai_decisions = {}
    if dual.agent is not None:
        for d in dual.agent.logger.decision_log:
            if d.get("type") == "EMERGENCY_LIQUIDATION":
                continue
            ai_decisions[d["date"]] = d

    all_dates = sorted(set(algo_decisions.keys()) | set(ai_decisions.keys()))

    result = []
    for date in all_dates:
        algo = algo_decisions.get(date)
        ai = ai_decisions.get(date)

        # 计算权重差异
        weight_diffs = []
        decisions_match = True

        if algo and ai:
            algo_w = algo.get("target_weights", {})
            ai_w = ai.get("target_weights", {})
            all_codes = set(algo_w.keys()) | set(ai_w.keys())
            for code in sorted(all_codes):
                aw = algo_w.get(code, 0)
                iw = ai_w.get(code, 0)
                delta = iw - aw
                if abs(delta) > 0.001:
                    decisions_match = False
                    weight_diffs.append({
                        "ts_code": code,
                        "name": ETF_POOL.get(code, code),
                        "algo_weight": round(aw, 4),
                        "ai_weight": round(iw, 4),
                        "delta": round(delta, 4),
                    })
        elif algo and not ai:
            decisions_match = False  # AI 尚无数据

        entry = {
            "date": date,
            "algo": {
                "target_weights": algo.get("target_weights", {}),
                "reasoning": algo.get("reasoning", ""),
            } if algo else None,
            "ai": {
                "target_weights": ai.get("target_weights", {}),
                "reasoning": ai.get("reasoning", ""),
            } if ai else None,
            "momentum_rankings": (algo or ai or {}).get("momentum_rankings", []),
            "decisions_match": decisions_match,
            "weight_diffs": weight_diffs,
        }
        result.append(entry)

    return result


@router.get("/trades")
def compare_trades():
    """交易记录对比"""
    dual = get_dual_state()
    if dual.headless is None:
        raise HTTPException(503, "回测尚未完成")

    return {
        "algo_trades": dual.headless.logger.trade_log,
        "ai_trades": dual.agent.logger.trade_log if dual.agent else [],
    }
