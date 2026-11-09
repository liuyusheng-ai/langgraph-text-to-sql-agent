# BIRD Mini-Dev 评测结果

由 `python eval/run_bird_eval.py` 生成。模型 `qwen3.5:4b`（Ollama 本地，temperature 0，关闭思考），从 BIRD Mini-Dev SQLite 版 500 条中按难度分层抽样（每档 50 条，seed 42），Schema：全部表，使用题目自带的 evidence 提示。准确率为 BIRD 官方的执行准确率（EX）：预测 SQL 与标准 SQL 的结果集相同即为正确。

## 执行准确率

| 难度 | 题数 | 不修复（首次生成） | 自修复（最多 2 次） | 提升 |
| --- | --- | --- | --- | --- |
| 简单 | 50 | 60.0% | 62.0% | +2.0 pp |
| 中等 | 50 | 32.0% | 34.0% | +2.0 pp |
| 困难 | 49 | 12.2% | 16.3% | +4.1 pp |
| **合计** | 149 | 34.9% | 37.6% | +2.7 pp |

自修复：35 题触发（首次 SQL 被安全校验拦截或执行报错），修复后答对 4 题，首次答对但修复后变错 0 题。temperature 为 0 时首次生成的 SQL 与 `max_repairs=0` 的结果一致，所以“不修复”一列来自同一次运行。

延迟 P50 / P95：2449.7 ms / 11681.4 ms；平均每题 777 个输入 token、101 个输出 token。 另有 1 题标准 SQL 超时，已排除。

## 安全规则误伤（全部 500 条，不需要模型）

| 检查 | 误伤 |
| --- | --- |
| 标准 SQL 被安全校验拦截 | 0/500 |
| 正常问题被判为写操作意图而拒绝 | 0/500 |

## 逐题明细

| ID | 数据库 | 难度 | 状态 | 尝试次数 | 首次 | 最终 | 耗时 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | california_schools | simple | completed | 1 | ✅ | ✅ | 3893 |
| 46 | california_schools | simple | completed | 1 | ❌ | ❌ | 1991 |
| 47 | california_schools | moderate | completed | 1 | ✅ | ✅ | 2366 |
| 50 | california_schools | simple | failed | 3 | ❌ | ❌ | 6124 |
| 82 | california_schools | simple | completed | 2 | ❌ | ❌ | 3688 |
| 87 | california_schools | challenging | completed | 1 | ❌ | ❌ | 3037 |
| 89 | financial | moderate | failed | 3 | ❌ | ❌ | 4630 |
| 92 | financial | simple | completed | 1 | ✅ | ✅ | 2418 |
| 93 | financial | moderate | completed | 1 | ❌ | ❌ | 1942 |
| 98 | financial | moderate | completed | 1 | ❌ | ❌ | 2170 |
| 115 | financial | challenging | completed | 1 | ❌ | ❌ | 2450 |
| 116 | financial | challenging | completed | 1 | ❌ | ❌ | 7375 |
| 125 | financial | challenging | completed | 1 | ❌ | ❌ | 3346 |
| 128 | financial | moderate | completed | 1 | ❌ | ❌ | 1756 |
| 149 | financial | challenging | failed | 3 | ❌ | ❌ | 6998 |
| 169 | financial | challenging | completed | 1 | ❌ | ❌ | 8550 |
| 173 | financial | challenging | completed | 2 | ❌ | ❌ | 2992 |
| 195 | toxicology | simple | completed | 1 | ✅ | ✅ | 955 |
| 200 | toxicology | simple | completed | 1 | ❌ | ❌ | 1573 |
| 207 | toxicology | challenging | completed | 1 | ❌ | ❌ | 1570 |
| 208 | toxicology | moderate | completed | 2 | ❌ | ❌ | 3110 |
| 218 | toxicology | challenging | completed | 1 | ❌ | ❌ | 3312 |
| 219 | toxicology | challenging | completed | 1 | ❌ | ❌ | 2942 |
| 226 | toxicology | moderate | completed | 1 | ❌ | ❌ | 1907 |
| 227 | toxicology | simple | completed | 1 | ✅ | ✅ | 1465 |
| 243 | toxicology | moderate | completed | 1 | ❌ | ❌ | 3542 |
| 248 | toxicology | simple | completed | 1 | ❌ | ❌ | 3345 |
| 249 | toxicology | challenging | completed | 1 | ❌ | ❌ | 2653 |
| 260 | toxicology | moderate | completed | 2 | ❌ | ❌ | 4817 |
| 268 | toxicology | challenging | completed | 1 | ✅ | ✅ | 1536 |
| 281 | toxicology | challenging | completed | 1 | ❌ | ❌ | 2386 |
| 282 | toxicology | challenging | completed | 1 | ✅ | ✅ | 2606 |
| 346 | card_games | moderate | completed | 1 | ✅ | ✅ | 2387 |
| 347 | card_games | moderate | completed | 1 | ❌ | ❌ | 2557 |
| 358 | card_games | simple | completed | 1 | ❌ | ❌ | 862 |
| 366 | card_games | simple | completed | 1 | ❌ | ❌ | 1376 |
| 377 | card_games | simple | completed | 1 | ❌ | ❌ | 1264 |
| 379 | card_games | simple | completed | 1 | ✅ | ✅ | 647 |
| 391 | card_games | moderate | completed | 1 | ❌ | ❌ | 2072 |
| 409 | card_games | moderate | completed | 1 | ❌ | ❌ | 1433 |
| 415 | card_games | challenging | completed | 1 | ❌ | ❌ | 2400 |
| 422 | card_games | simple | completed | 3 | ❌ | ❌ | 5263 |
| 424 | card_games | simple | completed | 1 | ❌ | ❌ | 1590 |
| 440 | card_games | simple | completed | 1 | ❌ | ❌ | 1351 |
| 459 | card_games | moderate | completed | 1 | ❌ | ❌ | 2489 |
| 466 | card_games | moderate | failed | 3 | ❌ | ❌ | 4826 |
| 468 | card_games | moderate | completed | 1 | ✅ | ✅ | 1547 |
| 477 | card_games | challenging | completed | 1 | ❌ | ❌ | 1348 |
| 487 | card_games | challenging | completed | 1 | ❌ | ❌ | 2614 |
| 539 | codebase_community | simple | completed | 1 | ❌ | ❌ | 1143 |
| 549 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1401 |
| 557 | codebase_community | moderate | completed | 1 | ✅ | ✅ | 2205 |
| 565 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 2954 |
| 571 | codebase_community | moderate | failed | 3 | ❌ | ❌ | 6181 |
| 572 | codebase_community | moderate | completed | 1 | ✅ | ✅ | 1168 |
| 581 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 1069 |
| 584 | codebase_community | moderate | completed | 1 | ❌ | ❌ | 3672 |
| 634 | codebase_community | challenging | completed | 1 | ❌ | ❌ | 2452 |
| 669 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1184 |
| 671 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1485 |
| 678 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1794 |
| 701 | codebase_community | challenging | 已排除 | | | | |
| 705 | codebase_community | simple | completed | 1 | ✅ | ✅ | 1546 |
| 717 | superhero | simple | completed | 1 | ✅ | ✅ | 1836 |
| 724 | superhero | challenging | completed | 1 | ✅ | ✅ | 2078 |
| 732 | superhero | moderate | completed | 1 | ✅ | ✅ | 2779 |
| 736 | superhero | moderate | completed | 1 | ✅ | ✅ | 1932 |
| 743 | superhero | challenging | failed | 3 | ❌ | ❌ | 11755 |
| 747 | superhero | simple | completed | 1 | ✅ | ✅ | 684 |
| 750 | superhero | simple | completed | 1 | ✅ | ✅ | 1151 |
| 764 | superhero | simple | completed | 1 | ✅ | ✅ | 1321 |
| 765 | superhero | simple | completed | 1 | ✅ | ✅ | 1193 |
| 769 | superhero | challenging | failed | 3 | ❌ | ❌ | 10107 |
| 773 | superhero | challenging | completed | 1 | ✅ | ✅ | 1892 |
| 779 | superhero | simple | completed | 1 | ✅ | ✅ | 1603 |
| 781 | superhero | simple | completed | 1 | ✅ | ✅ | 1255 |
| 788 | superhero | challenging | completed | 1 | ✅ | ✅ | 2681 |
| 792 | superhero | simple | completed | 1 | ✅ | ✅ | 1712 |
| 819 | superhero | challenging | completed | 1 | ✅ | ✅ | 2345 |
| 824 | superhero | moderate | completed | 1 | ✅ | ✅ | 1863 |
| 859 | formula_1 | simple | completed | 1 | ✅ | ✅ | 2654 |
| 862 | formula_1 | simple | completed | 1 | ✅ | ✅ | 2531 |
| 869 | formula_1 | moderate | completed | 1 | ✅ | ✅ | 1637 |
| 894 | formula_1 | moderate | completed | 1 | ❌ | ❌ | 2326 |
| 896 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 3015 |
| 901 | formula_1 | simple | completed | 2 | ❌ | ✅ | 3792 |
| 910 | formula_1 | simple | completed | 1 | ✅ | ✅ | 818 |
| 933 | formula_1 | moderate | completed | 2 | ❌ | ✅ | 5504 |
| 954 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 3095 |
| 962 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 3246 |
| 963 | formula_1 | moderate | completed | 1 | ❌ | ❌ | 2558 |
| 971 | formula_1 | simple | completed | 1 | ❌ | ❌ | 1275 |
| 981 | formula_1 | moderate | completed | 1 | ❌ | ❌ | 3970 |
| 1002 | formula_1 | moderate | completed | 2 | ❌ | ❌ | 5792 |
| 1011 | formula_1 | challenging | completed | 1 | ❌ | ❌ | 1909 |
| 1028 | european_football_2 | challenging | completed | 1 | ❌ | ❌ | 4016 |
| 1029 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 2407 |
| 1037 | european_football_2 | challenging | failed | 3 | ❌ | ❌ | 7145 |
| 1039 | european_football_2 | simple | timeout | 1 | ❌ | ❌ | 32265 |
| 1057 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 10322 |
| 1076 | european_football_2 | challenging | completed | 2 | ❌ | ❌ | 12254 |
| 1079 | european_football_2 | simple | completed | 1 | ❌ | ❌ | 968 |
| 1080 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 1164 |
| 1084 | european_football_2 | challenging | completed | 1 | ❌ | ❌ | 2143 |
| 1096 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 1850 |
| 1107 | european_football_2 | moderate | completed | 1 | ❌ | ❌ | 1851 |
| 1110 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 2098 |
| 1141 | european_football_2 | moderate | completed | 1 | ✅ | ✅ | 1846 |
| 1144 | european_football_2 | simple | completed | 1 | ❌ | ❌ | 1804 |
| 1155 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 1598 |
| 1157 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 1577 |
| 1168 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 5543 |
| 1169 | thrombosis_prediction | challenging | rejected | 3 | ❌ | ❌ | 9244 |
| 1187 | thrombosis_prediction | moderate | completed | 1 | ❌ | ❌ | 2807 |
| 1189 | thrombosis_prediction | challenging | failed | 3 | ❌ | ❌ | 7335 |
| 1192 | thrombosis_prediction | challenging | completed | 1 | ❌ | ❌ | 2744 |
| 1220 | thrombosis_prediction | simple | completed | 1 | ✅ | ✅ | 1323 |
| 1231 | thrombosis_prediction | challenging | completed | 2 | ❌ | ✅ | 4888 |
| 1232 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 6334 |
| 1239 | thrombosis_prediction | challenging | completed | 3 | ❌ | ✅ | 7633 |
| 1241 | thrombosis_prediction | challenging | rejected | 3 | ❌ | ❌ | 10951 |
| 1242 | thrombosis_prediction | challenging | completed | 2 | ❌ | ❌ | 8120 |
| 1243 | thrombosis_prediction | challenging | completed | 3 | ❌ | ❌ | 11305 |
| 1247 | thrombosis_prediction | challenging | completed | 1 | ❌ | ❌ | 2473 |
| 1257 | thrombosis_prediction | challenging | failed | 3 | ❌ | ❌ | 6312 |
| 1265 | thrombosis_prediction | moderate | failed | 3 | ❌ | ❌ | 5785 |
| 1267 | thrombosis_prediction | moderate | completed | 2 | ❌ | ❌ | 3218 |
| 1270 | thrombosis_prediction | challenging | failed | 3 | ❌ | ❌ | 6471 |
| 1322 | student_club | moderate | completed | 2 | ❌ | ❌ | 6471 |
| 1323 | student_club | moderate | completed | 1 | ✅ | ✅ | 2102 |
| 1331 | student_club | simple | completed | 1 | ✅ | ✅ | 1609 |
| 1340 | student_club | moderate | completed | 1 | ❌ | ❌ | 4607 |
| 1344 | student_club | simple | completed | 1 | ✅ | ✅ | 1351 |
| 1350 | student_club | moderate | completed | 2 | ❌ | ❌ | 4127 |
| 1361 | student_club | simple | completed | 1 | ✅ | ✅ | 1083 |
| 1371 | student_club | simple | completed | 1 | ✅ | ✅ | 1294 |
| 1378 | student_club | simple | completed | 1 | ✅ | ✅ | 575 |
| 1387 | student_club | moderate | failed | 3 | ❌ | ❌ | 5454 |
| 1394 | student_club | simple | completed | 1 | ✅ | ✅ | 1288 |
| 1432 | student_club | moderate | completed | 2 | ❌ | ❌ | 8528 |
| 1460 | student_club | challenging | completed | 1 | ❌ | ❌ | 1938 |
| 1464 | student_club | challenging | completed | 1 | ❌ | ❌ | 1930 |
| 1473 | debit_card_specializing | moderate | completed | 1 | ❌ | ❌ | 12663 |
| 1481 | debit_card_specializing | challenging | completed | 1 | ❌ | ❌ | 27669 |
| 1482 | debit_card_specializing | challenging | completed | 2 | ❌ | ❌ | 68985 |
| 1498 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 11681 |
| 1507 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 1563 |
| 1521 | debit_card_specializing | moderate | completed | 1 | ✅ | ✅ | 2846 |
| 1525 | debit_card_specializing | simple | completed | 1 | ❌ | ❌ | 3046 |
| 1533 | debit_card_specializing | moderate | completed | 1 | ❌ | ❌ | 21949 |
