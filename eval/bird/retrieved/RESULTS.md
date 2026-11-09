# BIRD Mini-Dev 评测结果

由 `python eval/run_bird_eval.py` 生成。模型 `qwen3.5:4b`（Ollama 本地，temperature 0，关闭思考），从 BIRD Mini-Dev SQLite 版 500 条中按难度分层抽样（每档 50 条，seed 42），Schema：按问题关键词检索，使用题目自带的 evidence 提示。准确率为 BIRD 官方的执行准确率（EX）：预测 SQL 与标准 SQL 的结果集相同即为正确。

## 执行准确率

| 难度 | 题数 | 不修复（首次生成） | 自修复（最多 2 次） | 提升 |
| --- | --- | --- | --- | --- |
| 简单 | 50 | 52.0% | 54.0% | +2.0 pp |
| 中等 | 50 | 26.0% | 34.0% | +8.0 pp |
| 困难 | 49 | 6.1% | 10.2% | +4.1 pp |
| **合计** | 149 | 28.2% | 32.9% | +4.7 pp |

自修复：42 题触发（首次 SQL 被安全校验拦截或执行报错），修复后答对 7 题，首次答对但修复后变错 0 题。temperature 为 0 时首次生成的 SQL 与 `max_repairs=0` 的结果一致，所以“不修复”一列来自同一次运行。

延迟 P50 / P95：3169.2 ms / 53315.6 ms；平均每题 666 个输入 token、102 个输出 token。 另有 1 题标准 SQL 超时，已排除。

## 安全规则误伤（全部 500 条，不需要模型）

| 检查 | 误伤 |
| --- | --- |
| 标准 SQL 被安全校验拦截 | 0/500 |
| 正常问题被判为写操作意图而拒绝 | 0/500 |

## 逐题明细

| ID | 数据库 | 难度 | 状态 | 尝试次数 | 首次 | 最终 | 耗时 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | california_schools | simple | completed | 1 | ❌ | ❌ | 878 |
| 46 | california_schools | simple | completed | 1 | ❌ | ❌ | 1749 |
| 47 | california_schools | moderate | completed | 1 | ✅ | ✅ | 2522 |
| 50 | california_schools | simple | completed | 1 | ❌ | ❌ | 1625 |
| 82 | california_schools | simple | completed | 1 | ❌ | ❌ | 13142 |
| 87 | california_schools | challenging | completed | 1 | ❌ | ❌ | 3144 |
| 89 | financial | moderate | completed | 1 | ❌ | ❌ | 1545 |
| 92 | financial | simple | completed | 1 | ✅ | ✅ | 2235 |
| 93 | financial | moderate | completed | 1 | ❌ | ❌ | 2142 |
| 98 | financial | moderate | completed | 1 | ❌ | ❌ | 2461 |
| 115 | financial | challenging | completed | 1 | ❌ | ❌ | 2640 |
| 116 | financial | challenging | failed | 3 | ❌ | ❌ | 35576 |
| 125 | financial | challenging | completed | 1 | ❌ | ❌ | 15195 |
| 128 | financial | moderate | completed | 1 | ❌ | ❌ | 17526 |
| 149 | financial | challenging | completed | 1 | ❌ | ❌ | 2348 |
| 169 | financial | challenging | failed | 3 | ❌ | ❌ | 36952 |
| 173 | financial | challenging | failed | 3 | ❌ | ❌ | 17334 |
| 195 | toxicology | simple | completed | 1 | ✅ | ✅ | 997 |
| 200 | toxicology | simple | completed | 1 | ❌ | ❌ | 1486 |
| 207 | toxicology | challenging | completed | 1 | ❌ | ❌ | 1333 |
| 208 | toxicology | moderate | completed | 2 | ❌ | ✅ | 2943 |
| 218 | toxicology | challenging | completed | 1 | ❌ | ❌ | 2570 |
| 219 | toxicology | challenging | completed | 1 | ❌ | ❌ | 12596 |
| 226 | toxicology | moderate | completed | 1 | ❌ | ❌ | 1873 |
| 227 | toxicology | simple | completed | 1 | ✅ | ✅ | 1993 |
| 243 | toxicology | moderate | completed | 1 | ❌ | ❌ | 11872 |
| 248 | toxicology | simple | completed | 1 | ❌ | ❌ | 1611 |
| 249 | toxicology | challenging | completed | 1 | ❌ | ❌ | 1531 |
| 260 | toxicology | moderate | completed | 2 | ❌ | ✅ | 4107 |
| 268 | toxicology | challenging | completed | 1 | ❌ | ❌ | 1574 |
| 281 | toxicology | challenging | completed | 1 | ❌ | ❌ | 2268 |
| 282 | toxicology | challenging | completed | 1 | ❌ | ❌ | 3169 |
| 346 | card_games | moderate | completed | 1 | ✅ | ✅ | 2494 |
| 347 | card_games | moderate | completed | 1 | ❌ | ❌ | 2653 |
| 358 | card_games | simple | completed | 1 | ❌ | ❌ | 1171 |
| 366 | card_games | simple | completed | 1 | ✅ | ✅ | 1475 |
| 377 | card_games | simple | completed | 2 | ❌ | ❌ | 30173 |
| 379 | card_games | simple | completed | 1 | ✅ | ✅ | 657 |
| 391 | card_games | moderate | completed | 1 | ❌ | ❌ | 2152 |
| 409 | card_games | moderate | completed | 1 | ❌ | ❌ | 1499 |
| 415 | card_games | challenging | completed | 1 | ❌ | ❌ | 2589 |
| 422 | card_games | simple | completed | 3 | ❌ | ❌ | 5520 |
| 424 | card_games | simple | completed | 1 | ❌ | ❌ | 1645 |
| 440 | card_games | simple | completed | 1 | ❌ | ❌ | 28684 |
| 459 | card_games | moderate | completed | 1 | ❌ | ❌ | 26267 |
| 466 | card_games | moderate | completed | 1 | ✅ | ✅ | 33937 |
| 468 | card_games | moderate | completed | 1 | ✅ | ✅ | 25192 |
| 477 | card_games | challenging | completed | 1 | ❌ | ❌ | 28172 |
| 487 | card_games | challenging | completed | 1 | ❌ | ❌ | 26568 |
| 539 | codebase_community | simple | completed | 1 | ❌ | ❌ | 15492 |
| 549 | codebase_community | simple | completed | 1 | ✅ | ✅ | 30631 |
| 557 | codebase_community | moderate | completed | 1 | ✅ | ✅ | 2350 |
| 565 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 2980 |
| 571 | codebase_community | moderate | failed | 3 | ❌ | ❌ | 6270 |
| 572 | codebase_community | moderate | completed | 1 | ✅ | ✅ | 1177 |
| 581 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 1208 |
| 584 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 3210 |
| 634 | codebase_community | challenging | completed | 1 | ❌ | ❌ | 2356 |
| 669 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1217 |
| 671 | codebase_community | simple | completed | 2 | ❌ | ❌ | 2922 |
| 678 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1913 |
| 701 | codebase_community | challenging | 已排除 | | | | |
| 705 | codebase_community | simple | completed | 1 | ✅ | ✅ | 13922 |
| 717 | superhero | simple | completed | 2 | ❌ | ❌ | 13442 |
| 724 | superhero | challenging | completed | 1 | ✅ | ✅ | 14700 |
| 732 | superhero | moderate | failed | 3 | ❌ | ❌ | 8350 |
| 736 | superhero | moderate | completed | 3 | ❌ | ✅ | 23572 |
| 743 | superhero | challenging | completed | 2 | ❌ | ❌ | 7284 |
| 747 | superhero | simple | completed | 1 | ✅ | ✅ | 712 |
| 750 | superhero | simple | completed | 1 | ✅ | ✅ | 1260 |
| 764 | superhero | simple | completed | 1 | ✅ | ✅ | 1405 |
| 765 | superhero | simple | completed | 1 | ❌ | ❌ | 769 |
| 769 | superhero | challenging | failed | 3 | ❌ | ❌ | 8311 |
| 773 | superhero | challenging | completed | 1 | ✅ | ✅ | 1899 |
| 779 | superhero | simple | failed | 3 | ❌ | ❌ | 5472 |
| 781 | superhero | simple | completed | 1 | ✅ | ✅ | 1263 |
| 788 | superhero | challenging | completed | 1 | ❌ | ❌ | 3386 |
| 792 | superhero | simple | completed | 2 | ❌ | ❌ | 2618 |
| 819 | superhero | challenging | completed | 1 | ✅ | ✅ | 2420 |
| 824 | superhero | moderate | failed | 3 | ❌ | ❌ | 4949 |
| 859 | formula_1 | simple | completed | 1 | ✅ | ✅ | 2618 |
| 862 | formula_1 | simple | completed | 1 | ✅ | ✅ | 2050 |
| 869 | formula_1 | moderate | completed | 1 | ✅ | ✅ | 2040 |
| 894 | formula_1 | moderate | failed | 3 | ❌ | ❌ | 17412 |
| 896 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 10188 |
| 901 | formula_1 | simple | completed | 2 | ❌ | ✅ | 18478 |
| 910 | formula_1 | simple | completed | 1 | ✅ | ✅ | 13509 |
| 933 | formula_1 | moderate | completed | 2 | ❌ | ✅ | 5597 |
| 954 | formula_1 | challenging | failed | 3 | ❌ | ❌ | 9068 |
| 962 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 3465 |
| 963 | formula_1 | moderate | completed | 1 | ❌ | ❌ | 2544 |
| 971 | formula_1 | simple | completed | 1 | ✅ | ✅ | 1312 |
| 981 | formula_1 | moderate | completed | 2 | ❌ | ❌ | 8367 |
| 1002 | formula_1 | moderate | completed | 2 | ❌ | ❌ | 5294 |
| 1011 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 1920 |
| 1028 | european_football_2 | challenging | completed | 1 | ❌ | ❌ | 4055 |
| 1029 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 2317 |
| 1037 | european_football_2 | challenging | failed | 3 | ❌ | ❌ | 7841 |
| 1039 | european_football_2 | simple | timeout | 1 | ❌ | ❌ | 32259 |
| 1057 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 3055 |
| 1076 | european_football_2 | challenging | completed | 2 | ❌ | ❌ | 9190 |
| 1079 | european_football_2 | simple | completed | 1 | ✅ | ✅ | 811 |
| 1080 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 1796 |
| 1084 | european_football_2 | challenging | completed | 1 | ❌ | ❌ | 2190 |
| 1096 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 1978 |
| 1107 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 1851 |
| 1110 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 2914 |
| 1141 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 3742 |
| 1144 | european_football_2 | simple | completed | 1 | ❌ | ❌ | 2122 |
| 1155 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 1595 |
| 1157 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 1584 |
| 1168 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 5560 |
| 1169 | thrombosis_prediction | challenging | rejected | 3 | ❌ | ❌ | 9070 |
| 1187 | thrombosis_prediction | moderate | completed | 1 | ❌ | ❌ | 2751 |
| 1189 | thrombosis_prediction | challenging | failed | 3 | ❌ | ❌ | 33743 |
| 1192 | thrombosis_prediction | challenging | completed | 1 | ❌ | ❌ | 28270 |
| 1220 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 28431 |
| 1231 | thrombosis_prediction | challenging | completed | 2 | ❌ | ✅ | 60220 |
| 1232 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 51066 |
| 1239 | thrombosis_prediction | challenging | completed | 3 | ❌ | ✅ | 83557 |
| 1241 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 68332 |
| 1242 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 16851 |
| 1243 | thrombosis_prediction | challenging | completed | 3 | ❌ | ❌ | 11286 |
| 1247 | thrombosis_prediction | challenging | completed | 1 | ❌ | ❌ | 28544 |
| 1257 | thrombosis_prediction | challenging | completed | 3 | ❌ | ❌ | 85210 |
| 1265 | thrombosis_prediction | moderate | failed | 3 | ❌ | ❌ | 83015 |
| 1267 | thrombosis_prediction | moderate | failed | 3 | ❌ | ❌ | 91056 |
| 1270 | thrombosis_prediction | challenging | failed | 3 | ❌ | ❌ | 79499 |
| 1322 | student_club | moderate | completed | 1 | ❌ | ❌ | 28078 |
| 1323 | student_club | moderate | completed | 1 | ✅ | ✅ | 27853 |
| 1331 | student_club | simple | completed | 1 | ✅ | ✅ | 25660 |
| 1340 | student_club | moderate | completed | 1 | ❌ | ❌ | 31292 |
| 1344 | student_club | simple | completed | 1 | ✅ | ✅ | 27805 |
| 1350 | student_club | moderate | completed | 1 | ❌ | ❌ | 26739 |
| 1361 | student_club | simple | completed | 1 | ✅ | ✅ | 24280 |
| 1371 | student_club | simple | failed | 3 | ❌ | ❌ | 53316 |
| 1378 | student_club | simple | completed | 1 | ✅ | ✅ | 589 |
| 1387 | student_club | moderate | failed | 3 | ❌ | ❌ | 6864 |
| 1394 | student_club | simple | completed | 1 | ✅ | ✅ | 1236 |
| 1432 | student_club | moderate | completed | 2 | ❌ | ❌ | 5939 |
| 1460 | student_club | challenging | completed | 1 | ❌ | ❌ | 1908 |
| 1464 | student_club | challenging | completed | 1 | ❌ | ❌ | 1869 |
| 1473 | debit_card_specializing | moderate | completed | 1 | ✅ | ✅ | 2215 |
| 1481 | debit_card_specializing | challenging | completed | 1 | ❌ | ❌ | 9502 |
| 1482 | debit_card_specializing | challenging | completed | 1 | ❌ | ❌ | 10651 |
| 1498 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 1016 |
| 1507 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 1032 |
| 1521 | debit_card_specializing | moderate | completed | 1 | ✅ | ✅ | 2835 |
| 1525 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 1684 |
| 1533 | debit_card_specializing | moderate | completed | 2 | ❌ | ❌ | 5585 |
