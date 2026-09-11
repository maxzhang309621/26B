# Q3 官方演练基线结果

**当前最佳：** `q3-best-20260911-1824`（见 `../baselines.md`）

| 文件 | 内容 |
|------|------|
| `official_best_20260911_1824_5.json` | **当前最佳**：今晚 18:24 官方问题3演练 5 局，均时 **5000.8 s**，5/5，371 s/源 |
| `official_baseline_round3_q12_10.json` | 历史对照：较早 10 局，均时 5245.4 s，10/10（不再作对比基线） |
| `mock_round3_q12_80.json` | 本地 mock-80 摘要，均时 **5157 s**，80/80 |

策略：`HuntPolicy(directional=False)` — Step 7 默认，8×1200 + 顺路复测/延后专程 + `locate_quality` / `next_stations`。仅演练，未碰正式测试。
