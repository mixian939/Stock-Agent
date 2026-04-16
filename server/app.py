"""FastAPI 后端：仪表盘 API + Agent 聊天接口"""

from __future__ import annotations

from contextlib import asynccontextmanager

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from stock_agent.server.state import run_headless_and_store, run_agent_and_store, get_state, get_dual_state, reset_state
from stock_agent.server.dashboard_routes import router as dashboard_router
from stock_agent.server.compare_routes import router as compare_router
from stock_agent.agent.tools import TradingToolkit
from stock_agent.agent.trading_agent import create_trading_agent


# --- Agent 实例（聊天用）---
_agent = None


def _get_or_create_agent():
    global _agent
    if _agent is None:
        state = get_state()
        if state is None:
            return None
        toolkit = TradingToolkit(
            state.feed, state.portfolio, state.tracker, state.logger,
        )
        _agent = create_trading_agent(toolkit)
    return _agent


# --- 生命周期 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Server] 启动中... 正在运行 headless 回测")
    run_headless_and_store()
    print("[Server] Headless 回测完成，服务就绪")
    print("[Server] 后台启动 Agent 回测...")
    threading.Thread(target=run_agent_and_store, daemon=True).start()
    yield


# --- FastAPI App ---
app = FastAPI(
    title="ETF 动量轮动交易系统",
    description="Agent 量化交易系统 - 仪表盘 & 聊天",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(compare_router)


# --- 聊天接口 ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    agent = _get_or_create_agent()
    if agent is None:
        return ChatResponse(reply="系统尚未就绪，请稍后再试")

    response = agent.run(req.message)
    content = response.content if response else "Agent 未返回响应"
    return ChatResponse(reply=content)


_backtest_lock = threading.Lock()


class BacktestRequest(BaseModel):
    backtest_start: str | None = None
    data_end: str | None = None


def _run_full_backtest(backtest_start: str | None, data_end: str | None):
    """后台线程：依次运行 headless + agent 回测"""
    global _agent
    try:
        run_headless_and_store(backtest_start=backtest_start, data_end=data_end)
        _agent = None
        run_agent_and_store(backtest_start=backtest_start, data_end=data_end)
    finally:
        _backtest_lock.release()


@app.post("/api/backtest/run")
def run_backtest(req: BacktestRequest):
    if not _backtest_lock.acquire(blocking=False):
        return JSONResponse(status_code=409, content={"detail": "回测正在运行中，请等待完成"})
    reset_state()
    threading.Thread(
        target=_run_full_backtest,
        args=(req.backtest_start, req.data_end),
        daemon=True,
    ).start()
    return {"status": "started"}


@app.get("/api/health")
def health():
    state = get_state()
    dual = get_dual_state()
    return {
        "status": "ok" if state else "initializing",
        "backtest_ready": state is not None,
        "agent_status": dual.agent_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7777)
