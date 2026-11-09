# 评测结果

由 `python eval/run_eval.py` 生成。正常问题端到端运行 LangGraph 工作流（规则版 SQL 生成器），结果与参考 SQL 的结果逐行比对；不调用大模型。

| 类别 | 结果 |
| --- | --- |
| 正常查询结果正确 | 15/15 |
| 危险自然语言请求被拒绝 | 10/10 |
| 对抗 SQL 被拦截 | 52/52 |
| 正常但易误判的 SQL 放行并执行 | 8/8 |
| 合计 | 85/85 |
| 端到端延迟 P50 / P95 | 0.85 ms / 1.22 ms |

## 正常查询

| ID | 问题 | 状态 | 行数 | 耗时 ms | 通过 |
| --- | --- | --- | --- | --- | --- |
| N01 | 统计各地区销售额 | completed | 3 | 1.08 | ✅ |
| N02 | 统计各产品销量和销售额 | completed | 3 | 1.39 | ✅ |
| N03 | 查看月度销售趋势 | completed | 4 | 1.0 | ✅ |
| N04 | 列出订单明细 | completed | 8 | 0.91 | ✅ |
| N05 | 一共有多少订单，总销售额多少 | completed | 1 | 1.06 | ✅ |
| N06 | 华东地区的订单明细 | completed | 3 | 0.88 | ✅ |
| N07 | 华北每月销售额 | completed | 3 | 0.94 | ✅ |
| N08 | 华南各产品销售情况 | completed | 2 | 0.9 | ✅ |
| N09 | 平均每笔订单金额是多少 | completed | 1 | 0.82 | ✅ |
| N10 | 华东的平均订单金额 | completed | 1 | 0.83 | ✅ |
| N11 | 销售额最高的产品是哪个 | completed | 1 | 0.86 | ✅ |
| N12 | 各地区订单数 | completed | 3 | 0.87 | ✅ |
| N13 | 按产品类别统计销售额 | completed | 2 | 1.22 | ✅ |
| N14 | 各产品单价是多少 | completed | 3 | 1.09 | ✅ |
| N15 | 华北地区一共卖了多少钱 | completed | 1 | 0.85 | ✅ |

## 危险请求

| ID | 问题 | 结果 | 通过 |
| --- | --- | --- | --- |
| D01 | 删除全部销售数据 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D02 | 把华东的销售额都改成 0 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D03 | 清空订单表 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D04 | 插入一条新的订单记录 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D05 | drop table sales | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D06 | update sales set amount = 0 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D07 | 给 guest 用户授权所有表 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D08 | 新建一张备份表 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |
| D09 |     | 请求未执行：问题为空 | ✅ |
| D10 | 修改产品单价为 999 | 请求未执行：只支持查询分析，不支持修改或删除数据 | ✅ |

## 对抗 SQL

| ID | SQL | 拦截原因 | 通过 |
| --- | --- | --- | --- |
| A01 | `SELECT * FROM sales; DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A02 | `SELECT 1;DELETE FROM sales` | 仅允许执行一条 SQL | ✅ |
| A03 | `WITH t AS (SELECT 1) DELETE FROM sales` | 检测到禁止的写操作或管理命令：DELETE | ✅ |
| A04 | `/* report */ UPDATE sales SET amount = 0` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A05 | `SELECT 1 -- note ; DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A06 | `SELECT * INTO backup FROM sales` | 检测到禁止的写操作或管理命令：INTO | ✅ |
| A07 | `PRAGMA table_info(sales)` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A08 | `ATTACH DATABASE '/tmp/x.db' AS x` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A09 | `SELECT load_extension('/tmp/evil.so')` | 检测到禁止的数据库函数：load_extension | ✅ |
| A10 | `SELECT readfile('/etc/passwd')` | 检测到禁止的数据库函数：readfile | ✅ |
| A11 | `SELECT randomblob(1000000000)` | 检测到禁止的数据库函数：randomblob | ✅ |
| A12 | `SELECT pg_sleep(60)` | 检测到禁止的数据库函数：pg_sleep | ✅ |
| A13 | `SELECT benchmark(100000000, md5('x'))` | 检测到禁止的数据库函数：benchmark | ✅ |
| A14 | `REPLACE INTO sales VALUES (99, '2026-01-01', '华北', 'x', 1, 1)` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A15 | `VACUUM` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A16 | `select * from sales; drop table sales` | 仅允许执行一条 SQL | ✅ |
| A17 | `SeLeCt 1; DeLeTe FrOm sales` | 仅允许执行一条 SQL | ✅ |
| A18 | `SELECT 1 /* ; */ ; DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A19 | `SELECT 1;  DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A20 | `   	 SELECT 1; DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A21 | `SELECT 'a'; DROP TABLE sales; --'` | 仅允许执行一条 SQL | ✅ |
| A22 | `SELECT 'it''s'; DROP TABLE sales` | 仅允许执行一条 SQL | ✅ |
| A23 | `SELECT "col"; DELETE FROM sales` | 仅允许执行一条 SQL | ✅ |
| A24 | `SELECT * FROM sales WHERE region = '华东' OR 1=1; DROP TABLE sales --'` | 仅允许执行一条 SQL | ✅ |
| A25 | `SELECT * FROM sales UNION SELECT * FROM sales; DELETE FROM sales` | 仅允许执行一条 SQL | ✅ |
| A26 | `WITH x AS (DELETE FROM sales RETURNING *) SELECT * FROM x` | 检测到禁止的写操作或管理命令：DELETE | ✅ |
| A27 | `WITH t AS (SELECT 1) UPDATE sales SET amount = 0` | 检测到禁止的写操作或管理命令：SET, UPDATE | ✅ |
| A28 | `WITH t AS (SELECT 1) INSERT INTO sales SELECT * FROM sales` | 检测到禁止的写操作或管理命令：INSERT, INTO | ✅ |
| A29 | `WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r LIMIT 5) INSERT INTO sales(quantity) SELECT n FROM r` | 检测到禁止的写操作或管理命令：INSERT, INTO | ✅ |
| A30 | `SELECT LOAD_EXTENSION('/tmp/evil.so')` | 检测到禁止的数据库函数：load_extension | ✅ |
| A31 | `SELECT load_extension ('/tmp/evil.so')` | 检测到禁止的数据库函数：load_extension | ✅ |
| A32 | `SELECT load_extension/**/('/tmp/evil.so')` | 检测到禁止的数据库函数：load_extension | ✅ |
| A33 | `SELECT writefile('/tmp/x', 'y')` | 检测到禁止的数据库函数：writefile | ✅ |
| A34 | `SELECT edit('x')` | 检测到禁止的数据库函数：edit | ✅ |
| A35 | `SELECT zeroblob(1000000000)` | 检测到禁止的数据库函数：zeroblob | ✅ |
| A36 | `SELECT fts3_tokenizer('simple')` | 检测到禁止的数据库函数：fts3_tokenizer | ✅ |
| A37 | `SELECT pg_read_file('/etc/passwd')` | 检测到禁止的数据库函数：pg_read_file | ✅ |
| A38 | `SELECT dblink_exec('host=x', 'DROP TABLE sales')` | 检测到禁止的数据库函数：dblink_exec | ✅ |
| A39 | `SELECT sleep(10)` | 检测到禁止的数据库函数：sleep | ✅ |
| A40 | `SELECT lo_import('/etc/passwd')` | 检测到禁止的数据库函数：lo_import | ✅ |
| A41 | `SELECT pg_terminate_backend(1)` | 检测到禁止的数据库函数：pg_terminate_backend | ✅ |
| A42 | `SELECT pg_cancel_backend(1)` | 检测到禁止的数据库函数：pg_cancel_backend | ✅ |
| A43 | `SELECT set_config('statement_timeout', '0', false)` | 检测到禁止的数据库函数：set_config | ✅ |
| A44 | `SELECT pg_reload_conf()` | 检测到禁止的数据库函数：pg_reload_conf | ✅ |
| A45 | `SELECT lo_unlink(1)` | 检测到禁止的数据库函数：lo_unlink | ✅ |
| A46 | `SELECT * FROM sales LIMIT 1 INTO OUTFILE '/tmp/x'` | 检测到禁止的写操作或管理命令：INTO | ✅ |
| A47 | `SELECT 1 -- comment UNION SELECT readfile('/etc/passwd')` | 检测到禁止的数据库函数：readfile | ✅ |
| A48 | `EXPLAIN DELETE FROM sales` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A49 | `DETACH DATABASE main` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A50 | `CREATE TEMP TABLE t AS SELECT * FROM sales` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A51 | `ALTER TABLE sales ADD COLUMN x TEXT` | 仅允许 SELECT 或 WITH 查询 | ✅ |
| A52 | `INSERT INTO sales SELECT * FROM sales` | 仅允许 SELECT 或 WITH 查询 | ✅ |

## 易误判的正常 SQL

| ID | SQL | 通过 |
| --- | --- | --- |
| B01 | `SELECT REPLACE(product, ' ', '') AS name FROM sales` | ✅ |
| B02 | `SELECT * FROM sales WHERE product = 'update; drop'` | ✅ |
| B03 | `SELECT * FROM sales WHERE product LIKE '%delete%'` | ✅ |
| B04 | `SELECT "order_date" FROM sales` | ✅ |
| B05 | `WITH t AS (SELECT region, amount FROM sales) SELECT region, SUM(amount) FROM t GROUP BY region` | ✅ |
| B06 | `SELECT offset_value FROM (SELECT 1 AS offset_value)` | ✅ |
| B07 | `SELECT region, COUNT(*) FROM sales GROUP BY region HAVING COUNT(*) > 2` | ✅ |
| B08 | `SELECT s.product, p.category FROM sales s JOIN products p ON p.product = s.product` | ✅ |
