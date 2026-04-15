"""仪表盘 REST API：净值曲线、持仓、交易记录、绩效指标、回撤曲线"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from stock_agent.server.state import get_state

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/nav-history")
def nav_history():
    """净值曲线数据"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")
    return state.tracker.nav_history


@router.get("/current-positions")
def current_positions():
    """当前持仓（回测结束时的持仓）"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")

    prices = state.last_prices or state.feed.get_today_prices()
    portfolio = state.portfolio
    weights = portfolio.get_current_weights(prices)
    total = portfolio.get_total_value(prices)

    from stock_agent.config import ETF_POOL

    positions = []
    for code, shares in portfolio.positions.items():
        price = prices.get(code, 0)
        value = shares * price
        positions.append({
            "ts_code": code,
            "name": ETF_POOL.get(code, code),
            "shares": shares,
            "price": round(price, 3),
            "value": round(value, 2),
            "weight": round(weights.get(code, 0), 4),
        })

    return {
        "total_value": round(total, 2),
        "cash": round(portfolio.cash, 2),
        "positions": positions,
    }


@router.get("/trade-history")
def trade_history():
    """交易记录"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")
    return state.logger.trade_log


@router.get("/performance-metrics")
def performance_metrics():
    """绩效指标"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")
    metrics = state.tracker.get_metrics()
    metrics["total_trades"] = len(state.portfolio.order_history)
    return metrics


@router.get("/drawdown-curve")
def drawdown_curve():
    """回撤曲线数据"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")
    return [
        {"date": r["date"], "drawdown": r["drawdown"]}
        for r in state.tracker.nav_history
    ]


@router.get("/decision-history")
def decision_history():
    """调仓决策记录"""
    state = get_state()
    if state is None:
        raise HTTPException(503, "回测尚未完成")
    return state.logger.decision_log
