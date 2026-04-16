# ETF 动量轮动交易系统

一个带有双智能体决策机制的 ETF 量化交易演示项目。

这个项目做的事情可以用一句话概括：

1. 先抓取 ETF 历史行情数据
2. 用动量策略计算当前更强的资产类别
3. 在回测环境里模拟调仓
4. 用主智能体 + 本地金融子智能体一起分析并给出调仓建议
5. 通过前端页面把净值、回撤、持仓、交易和决策过程展示出来

---

## 一、项目简介

这个项目不是单纯的“量化回测脚本”，而是一个从数据获取、策略计算、智能体决策、日志记录到前端展示都比较完整的小型量化系统。

它有两个主要特点：

### 1. ETF 池变大了，但投资逻辑没有变复杂

项目现在维护的是 **14 只 ETF**，但依然只围绕 **7 个资产类别** 轮动：

1. 沪深300
2. 中证500
3. 创业板
4. 红利
5. 国债
6. 黄金
7. 纳指100

系统不是把 14 只 ETF 全部混在一起直接乱排，而是：

1. 先在每个类别里选出动量最强的那 1 只 ETF
2. 再让这 7 个类别代表去竞争

所以你可以理解为：

“池子更大了，但策略还是在做 7 大类资产轮动。”

### 2. 决策不是一个模型单独拍板

系统里有两个智能体：

1. 主智能体：`gpt-5.4`
2. 子智能体：本地金融模型 `fin-r1`

子智能体先看数据，给建议和评分。

主智能体再结合自己的判断，按下面的固定权重做最后决策：

```text
子智能体 60%
主智能体 40%
```

主智能体最终决定：

1. 调不调仓
2. 调哪些 ETF
3. 各自调到多少仓位
4. 为什么这么做

---

## 二、项目功能

当前项目支持以下能力：

1. 自动获取 ETF 历史日线数据
2. 本地缓存数据，避免重复下载
3. 纯策略回测
4. 双智能体回测
5. 最大回撤止损和冷却期
6. 结构化日志输出
7. FastAPI 提供后端接口
8. Next.js 前端可视化展示
9. 聊天式询问主智能体
10. 对比“算法策略”和“双智能体策略”

---

## 三、环境要求

这部分尽量按小白能直接照做的方式写。

### 3.1 推荐环境

本项目当前实测环境如下：

| 项目 | 版本 |
|------|------|
| Python | 建议 `3.10+` |
| Node.js | 实测 `v24.14.0` |
| pnpm | 实测 `10.32.0` |
| uv | 实测 `0.9.11` |

说明：

1. Python 建议使用 `3.10` 或更高版本
2. 前端需要 Node.js 环境
3. `pnpm` 用来安装和运行前端
4. `uv` 不是必须，但我实际测试时用它来跑 Python 命令和测试，比较方便

### 3.2 Python 依赖

后端核心依赖在 [requirements.txt](C:/Users/XOS/ai_learn/stock_agent/requirements.txt) 里：

| 包名 | 版本要求 |
|------|----------|
| fastapi | `>=0.115.0` |
| uvicorn | `>=0.24.0` |
| pydantic | `>=2.0` |
| agno | `>=2.5.17` |
| openai | `>=1.82.0` |
| tushare | `>=1.4.24` |
| jqdatasdk | `>=1.9.8` |
| pandas | `>=2.0` |
| numpy | `>=2.0` |

### 3.3 前端依赖

前端依赖在 [frontend/package.json](C:/Users/XOS/ai_learn/stock_agent/frontend/package.json) 里，核心版本如下：

| 包名 | 版本 |
|------|------|
| next | `16.2.3` |
| react | `19.2.4` |
| react-dom | `19.2.4` |
| recharts | `^3.8.1` |
| typescript | `^5` |
| eslint | `^9` |
| tailwindcss | `^4` |

---

## 四、安装方式

下面按最容易照着做的顺序来。

### 4.1 进入项目目录

```powershell
cd C:\Users\XOS\ai_learn\stock_agent
```

### 4.2 安装 Python 依赖

如果你用 `pip`：

```powershell
pip install -r requirements.txt
```

如果你用 `uv`：

```powershell
uv pip install -r requirements.txt
```

### 4.3 安装前端依赖

```powershell
cd frontend
pnpm install
cd ..
```

---

## 五、运行前你需要知道的配置

### 5.1 数据接口

项目数据层是这样设计的：

1. 先尝试 `Tushare`
2. 如果失败，再退到 `jqdatasdk`

也就是说，代码逻辑上是：

```text
Tushare 优先
JoinQuant / jqdatasdk 兜底
```

### 5.2 主智能体配置

主智能体在 [config.py](C:/Users/XOS/ai_learn/stock_agent/config.py) 中配置，当前使用：

1. OpenAI 兼容接口
2. 模型：`gpt-5.4`

### 5.3 子智能体配置

子智能体也在 [config.py](C:/Users/XOS/ai_learn/stock_agent/config.py) 中配置，当前默认值已经改成：

1. Base URL: `http://127.0.0.1:11434/v1`
2. API Key: `sk-lm-vjQeAz3R:ynyBRX4fNUWgGllzbpCE`
3. Model: `fin-r1`

也就是说，运行双智能体回测前，你要确保本地这个模型服务已经起来了。

### 5.4 如果你想换模型

可以直接改环境变量，或者直接改 [config.py](C:/Users/XOS/ai_learn/stock_agent/config.py)。

当前这些参数支持通过环境变量覆盖：

1. `LM_STUDIO_BASE_URL`
2. `LM_STUDIO_MODEL_ID`
3. `LM_STUDIO_API_KEY`

---

## 六、小白也能看懂的运行方式

这部分按“你想做什么”来写。

### 6.1 只想快速看看纯策略回测

这是最快的方式，不依赖主智能体和子智能体。

```powershell
cd C:\Users\XOS\ai_learn
uv run python -m stock_agent.run_backtest --headless
```

如果你不用 `uv`，也可以：

```powershell
cd C:\Users\XOS\ai_learn
python -m stock_agent.run_backtest --headless
```

这个模式会做的事：

1. 获取或读取 ETF 数据
2. 按动量规则轮动
3. 输出最终收益、回撤、交易次数等结果

适合：

1. 先确认策略主流程是否正常
2. 不想等大模型响应

### 6.2 想测试双智能体决策回测

先确认你的本地金融模型服务已经起来，再运行：

```powershell
cd C:\Users\XOS\ai_learn
uv run python -m stock_agent.run_backtest
```

这个模式会做的事：

1. 子智能体先分析市场并给建议
2. 主智能体再结合建议做最终调仓
3. 把决策、仓位、理由都写入日志

适合：

1. 看双智能体协作是否正常
2. 看调仓理由和模型输出

### 6.3 只想做一个短一点的烟雾测试

如果你不想每次都跑完整个 6 个月，可以像我测试时那样，只跑一个短区间。

示例：

```powershell
cd C:\Users\XOS\ai_learn
uv run python -c "from stock_agent.backtest.simulator import BacktestSimulator; from stock_agent.data.fetcher import DataFetcher; sim = BacktestSimulator(); sim.fetcher = DataFetcher(start='20241101', end='20250131'); sim.run_agent()"
```

这个命令的意思是：

1. 只抓到 `2025-01-31` 为止的数据
2. 实际只跑 1 个月左右的回测
3. 更适合做功能验证，而不是正式看半年绩效

### 6.4 想启动后端接口

```powershell
cd C:\Users\XOS\ai_learn
uv run python -m stock_agent.server.app
```

后端默认端口：

```text
http://127.0.0.1:7777
```

启动后，后端会：

1. 先自动跑一次 Headless 回测
2. 再在后台启动智能体回测

### 6.5 想启动前端页面

另开一个终端：

```powershell
cd C:\Users\XOS\ai_learn\stock_agent\frontend
pnpm dev
```

前端默认地址：

```text
http://127.0.0.1:3000
```

### 6.6 页面分别是做什么的

启动前后端后，可以打开：

1. `/`：仪表盘首页
2. `/chat`：主智能体聊天页
3. `/compare`：算法 vs 双智能体对比页

---

## 七、测试方式

### 7.1 运行后端单元测试

```powershell
cd C:\Users\XOS\ai_learn\stock_agent
uv run pytest tests -q
```

我最近一次实测结果：

```text
32 passed
```

### 7.2 运行前端代码检查

```powershell
cd C:\Users\XOS\ai_learn\stock_agent\frontend
pnpm lint
```

### 7.3 构建前端

```powershell
cd C:\Users\XOS\ai_learn\stock_agent\frontend
pnpm build
```

我最近一次实测：

1. `pnpm lint` 通过
2. `pnpm build` 通过

---

## 八、常见问题

### 8.1 为什么我运行双 Agent 回测很慢？

因为双 Agent 模式每个调仓日都要调用模型。

如果你只是想验证功能，建议：

1. 先跑 `--headless`
2. 或者把回测区间缩短成 1 个月

### 8.2 为什么有时子智能体会显示 fallback？

因为系统做了容错处理。

如果本地金融模型不可用、超时、返回格式不对，系统会退化到启发式建议，而不是整场回测直接崩掉。

### 8.3 为什么我要从 `C:\Users\XOS\ai_learn` 运行，而不是直接在项目目录里？

因为包名是 `stock_agent`。

从上一级目录运行更稳，像这样：

```powershell
cd C:\Users\XOS\ai_learn
uv run python -m stock_agent.run_backtest
```

### 8.4 如果前端 build 失败怎么办？

优先检查：

1. Node.js 是否安装
2. `pnpm install` 是否执行过
3. 是否从 `frontend` 目录里运行

---

## 九、项目结构

```text
stock_agent/
├─ agent/               # 智能体定义与双智能体协调层
├─ backtest/            # 回测模拟器
├─ data/                # 数据抓取、缓存、行情回放
├─ engine/              # 持仓、绩效、执行
├─ frontend/            # Next.js 前端
├─ logging_/            # 日志记录
├─ logs/                # 输出日志文件
├─ server/              # FastAPI 接口
├─ strategy/            # 动量策略
├─ tests/               # 单元测试
├─ config.py            # 全局配置
├─ run_backtest.py      # 回测入口
├─ TASK_PLAN.md         # 当前任务计划
└─ PROJECT_REPORT.md    # 当前这份项目说明
```

---

## 十、策略设计说明

### 10.1 ETF 池

当前 ETF 池共 14 只：

| 类别 | ETF 代码 | ETF 名称 |
|------|----------|----------|
| 沪深300 | 510300.SH | 沪深300ETF |
| 沪深300 | 159919.SZ | 嘉实沪深300ETF |
| 中证500 | 510500.SH | 中证500ETF |
| 中证500 | 159922.SZ | 嘉实中证500ETF |
| 创业板 | 159915.SZ | 创业板ETF |
| 创业板 | 159949.SZ | 创业板50ETF |
| 红利 | 510880.SH | 红利ETF |
| 红利 | 515180.SH | 红利ETF易方达 |
| 国债 | 511010.SH | 国债ETF |
| 国债 | 511260.SH | 十年国债ETF |
| 黄金 | 518880.SH | 黄金ETF |
| 黄金 | 159934.SZ | 黄金ETF易方达 |
| 纳指100 | 513100.SH | 纳指100ETF |
| 纳指100 | 159941.SZ | 纳指ETF广发 |

### 10.2 动量计算

```text
动量 = 今日收盘价 / 20个交易日前收盘价 - 1
```

### 10.3 当前轮动逻辑

流程如下：

1. 对 14 只 ETF 计算动量
2. 每个类别保留动量最高的 1 只 ETF
3. 得到 7 个类别代表 ETF
4. 从中取前 `TOP_N=2`
5. 若前 2 名都小于等于 0，则 100% 配置安全资产
6. 否则配置正动量类别代表
7. 单只 ETF 最大权重限制为 50%

### 10.4 风控逻辑

当前仍保留原有风控：

1. 最大回撤止损：`-8%`
2. 止损冷却期：`10` 个交易日
3. 调仓日：每周五

---

## 十一、双智能体决策说明

### 11.1 角色分工

子智能体负责：

1. 看市场快照
2. 输出建议仓位
3. 给类别代表 ETF 打分
4. 给出理由

主智能体负责：

1. 接收子智能体的建议
2. 给出自己的评分
3. 与子 Agent 的评分做加权融合
4. 决定最终仓位

### 11.2 固定权重

```text
最终加权分 = 子智能体评分 * 0.60 + 主智能体评分 * 0.40
```

### 11.3 记录到日志的内容

现在每次双智能体决策会在日志中记录：

1. 子智能体建议
2. 主智能体建议
3. 加权评分
4. 算法推荐仓位
5. 调仓前持仓
6. 最终目标仓位
7. 是否实际执行

---

## 十二、前端页面说明

### 12.1 首页 `/`

首页展示：

1. 净值曲线
2. 回撤曲线
3. 最终持仓
4. 最近交易记录
5. 最新双智能体裁决摘要
6. 数据源摘要

### 12.2 聊天页 `/chat`

这是主智能体的对话页面，可以问：

1. 当前策略逻辑
2. 某只 ETF 为什么入选
3. 当前绩效情况
4. 调仓逻辑说明

### 12.3 对比页 `/compare`

这里重点看：

1. 算法策略和双智能体策略净值对比
2. 回撤对比
3. 每次调仓决策差异
4. 子智能体建议
5. 主智能体建议
6. 60/40 加权分

---

## 十三、已完成验证

### 13.1 后端单元测试

已通过：

```text
32 passed
```

### 13.2 前端验证

已通过：

1. `pnpm lint`
2. `pnpm build`

### 13.3 1 个月双智能体烟雾测试

我按你提出的“测试不必每次都跑 6 个月”做了一次短回测验证。

结果：

1. 交易日：18 个
2. 最终资产：`1,005,946.12`
3. 总收益率：`+0.59%`
4. 最大回撤：`-2.52%`
5. 总交易次数：`4`

关键点：

1. 子智能体实际来源显示为 `lm_studio`
2. 主智能体来源显示为 `primary_llm`
3. 双智能体调仓链路已经实际跑通

### 13.4 6 个月纯策略基线验证

我也跑过完整纯策略基线回测，确认扩容 ETF 池后纯策略主流程没坏。

结果：

1. 最终资产：`1,134,338.24`
2. 总收益率：`+13.43%`
3. 年化收益：`+31.19%`
4. 最大回撤：`-4.41%`
5. 夏普比率：`1.83`
6. 总交易次数：`64`

---

## 十四、数据来源最终确认

这是你特别要求保留在最后的结论。

项目代码结构上仍然是：

```text
优先尝试 Tushare
失败后退到 JoinQuant / jqdatasdk
```

但是我在 **2026-04-16** 做了真实强制刷新测试，对当前 **14 只 ETF** 全部执行了 `fetch_all(force_refresh=True)`。

实际测试结果是：

1. 这次真实获取到的数据 **全部来自 `joinquant/jqdatasdk`**
2. 也就是说，当前实测落地的数据接口不是 `tushare`
3. 当前实测真正拿到数据的是 **聚宽的 `jqdatasdk`**

实测结果如下：

```text
510300.SH -> joinquant/jqdatasdk
159919.SZ -> joinquant/jqdatasdk
510500.SH -> joinquant/jqdatasdk
159922.SZ -> joinquant/jqdatasdk
159915.SZ -> joinquant/jqdatasdk
159949.SZ -> joinquant/jqdatasdk
510880.SH -> joinquant/jqdatasdk
515180.SH -> joinquant/jqdatasdk
511010.SH -> joinquant/jqdatasdk
511260.SH -> joinquant/jqdatasdk
518880.SH -> joinquant/jqdatasdk
159934.SZ -> joinquant/jqdatasdk
513100.SH -> joinquant/jqdatasdk
159941.SZ -> joinquant/jqdatasdk
```
