# LangGraph Text-to-SQL Agent

面向结构化数据自助分析场景的 Text-to-SQL 项目：用户输入自然语言问题，系统完成 Schema 检索、SQL 生成、安全校验、只读执行、结果解释和图表生成，并保留可复核的 SQL 与查询历史。

## 项目亮点

- 使用 LangGraph 编排 6 个节点：问题理解、Schema 检索、SQL 生成、安全校验、只读执行、结果解释。
- 提供受限自动修复路径，并以修复次数限制避免无限重试。
- 设置 SELECT/CTE 白名单、执行超时、最大返回行数、修复次数 4 类约束。
- 显式拦截 `INSERT`、`UPDATE`、`DELETE`、`DROP` 等写操作及多语句注入。
- 基于 FastAPI、SQLAlchemy 提供查询和历史记录接口；默认使用 SQLite，也可通过 `DATABASE_URL` 接入 SQLAlchemy 支持的数据库。
- 自动生成 Plotly 兼容图表配置，保留问题、SQL、结果和执行状态。
- 内置离线演示数据与规则模型，不配置任何 API Key 也可以运行和测试。

## 工作流

```text
自然语言问题
   -> 问题理解
   -> Schema 检索
   -> SQL 生成
   -> 安全校验 --失败且未超限--> 受限修复
   -> 只读执行
   -> 结果解释与图表
```

## 快速开始

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

打开 `http://127.0.0.1:8000/docs`，可直接调用：

```text
POST /api/query
GET  /api/history
GET  /healthz
```

请求示例：

```json
{
  "question": "统计各地区销售额"
}
```

也可以尝试“统计各产品销量”“查看月度销售趋势”或“列出订单明细”。

## 测试

```bash
pytest -q
```

测试覆盖正常分析、危险写操作、多语句注入、最大行数限制和查询历史。项目默认不连接外部模型，便于复现安全链路；接入真实大模型时，只需替换 `llm.py` 中的生成器接口，所有 SQL 仍必须经过 `SQLSafetyValidator`。

## 目录说明

```text
app.py          FastAPI 接口
workflow.py     LangGraph 六节点工作流
safety.py       SQL 白名单与边界控制
database.py     SQLAlchemy、演示数据与查询历史
llm.py          可替换的模型适配器
charting.py     Plotly 兼容图表配置
test_agent.py   自动化测试
```

## 安全说明

本项目用于学习和作品展示。演示环境应使用只读数据库账号；即使模型生成了危险 SQL，也不能依赖提示词作为唯一防线，必须保留服务端 SQL 校验、数据库权限隔离、查询超时与审计日志。

