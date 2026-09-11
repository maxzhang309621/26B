# Q3 官方演练基线结果

锁定基线：`q3-round3-q12`（见 `../baselines.md`）

| 文件 | 内容 |
|------|------|
| `official_baseline_round3_q12_10.json` | 官方问题3演练 10 局摘要，均时 **5245.4 s**，10/10 |
| `mock_round3_q12_80.json` | 本地 mock-80 摘要，均时 **5157 s**，80/80 |

策略：`HuntPolicy(directional=False)` — 8×1200 + 顺路复测/延后专程 + `locate_quality` / `next_stations`。仅演练，未碰正式测试。
