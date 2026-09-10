# 实现记录

## T1 几何核（2026-09-10）

- 文件：`src/geometry.py`、`src/tests/test_geometry.py`
- 冒烟：6 passed

## T2 协议与 mock（2026-09-10）

- 文件：`src/robot_client.py`、`src/mock_sim.py`、`src/tests/test_protocol.py`
- 冒烟：附件计时 105/111/194/199；6 passed

## T3 候选区（2026-09-10）

- 文件：`src/candidate.py`
- 沿示向点不在候选区；名义源旁侧推荐点交角 ∈[60°,120°]

## T4 覆盖航路（2026-09-10）

- 文件：`src/coverage.py`
- 问题 3：原点 + 8×1200 m，边界采样覆盖半径 1000 m 通过
- 问题 4：内圈 + 2000/2200/2450 m 外环

## T5 问题 3 策略（2026-09-10）

- 文件：`src/belief.py`、`src/policy.py`、`src/runner_q3.py`、`src/tests/test_q3.py`
- mock 种子 0/1/2，源个数 10/12/16，清除比例 = 1

## T6 问题 4 策略（2026-09-10）

- 文件：`src/runner_q4.py`、`src/tests/test_q4.py`
- 定向背面导致正交第二点失效；增加沿示向 12 m 蠕动逼近至 near/20 m 清除
- mock 种子 3/4（含朝外定向源）清除比例 = 1

## T7 可视化与 Q1 CLI（2026-09-10）

- 文件：`src/viz.py`、`src/q1_cli.py`
- 输出：`output/figures/q1_intersection.png` 等三张图
- `python q1_cli.py` 输出直径、包围圆、覆盖判定 JSON

## T8

- HTTP `HttpTransport` 已在 `robot_client.py`；问题3/4各一局演练全清
- 演练批量：`run_practice_batch.py`（只允许演练，命令行/界面/日志出现正式测试即中止）
- 启动器：`scripts/launch_simulator_for_practice.bat`（无障碍，便于自动点「开始问题X演练测试」）
- **禁止正式测试**：无正式测试入口，`--formal`/`--official` 直接退出

## 冒烟命令

```
cd 26B/src
python -m unittest tests.test_geometry tests.test_protocol tests.test_q3 tests.test_q4
python q1_cli.py
```

合计 17 tests OK。
