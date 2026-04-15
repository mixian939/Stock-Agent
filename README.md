## 运行方式

```bash
# 1. 无头回测（纯策略，秒级完成）
python -m stock_agent.run_backtest --headless

# 2. Agent 回测（LLM 自主决策，需要等待 LLM 响应）
python -m stock_agent.run_backtest

# 3. 启动 Web 服务
python -m stock_agent.server.app          # 后端 :7777
# 3.1 启动前端服务（另开终端）
cd stock_agent/frontend 
pnpm dev       # 前端 :3000

# 4. 运行单元测试
python -m pytest stock_agent/tests/ -v    # 27 个测试
```

---
