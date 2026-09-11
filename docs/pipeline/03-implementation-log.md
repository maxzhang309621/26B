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
- 问题 4：内圈（原点+8×1200 m）+ **一圈外环 16×2100 m**（去掉多余的 2000/2450 双环，缩短空驶）

## T5 问题 3 策略（2026-09-10）

- 文件：`src/belief.py`、`src/policy.py`、`src/runner_q3.py`、`src/tests/test_q3.py`
- mock 种子 0/1/2，源个数 10/12/16，清除比例 = 1

## T6 问题 4 策略（2026-09-10，Peterzhu 加速 2026-09-11）

- 文件：`src/runner_q4.py`、`src/policy.py`、`src/coverage.py`、`src/candidate.py`、`src/tests/test_q4.py`
- 原策略：定向源先沿示向 **12 m 蠕动**（最多 40 步），再交会；外环三圈约 53 航点。正确率高，空驶多。
- **改动（正确率不降、压虚拟时间）**
  1. 先做正交第二点交会（两侧都试，照顾定向背面），MEC≤20 m 再 `/clear`；蠕动改为 **大步长后备**，不再一听到达就爬行。
  2. 外环收成 **16 点 / 2100 m** 一圈，保证朝外 180° 半平面内仍有 ≤1000 m 听点。
- mock：朝外定向混合仍全清；Q4 平均总时约 20471 s → **11241 s（约 −45%）**；Q3 顺带约 8746 s → 6326 s。
- 官方演练（只跑演练，未碰正式测试）
  - 加速前对照局：15/15，平均约 1263 s/源
  - 加速后单局：16/16，平均约 790 s/源
  - **连续 10 局演练全清 100%**（10–16 源，含最多 14 个定向），平均虚拟时间约 11600 s
- 单元测试种子扩到 `(3,12,4),(4,10,6),(0,12,6),(5,16,8)`，清除比例 = 1

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

## T9–T11 问题 1/2 质量接口回灌（2026-09-11，`feat/q12-locate-kernel`）

- `locate_quality`：近共线禁止伪清除；`can_clear_20` 仅比最小包围圆与 20 m；圆心落在无信号 1000 m 内则再测。
- `next_stations` / `front_compatible`：全向先正交推荐点；定向先紧凑两侧，前瓣点优先，交角过差的近点丢弃。
- `HuntPolicy`：两站以上先问 `can_clear_20`；第二站列表接 `next_stations`，空则回退原 compact/recommend。
- 冒烟：`python -m unittest tests.test_geometry tests.test_candidate tests.test_q3 tests.test_q4 tests.test_protocol tests.test_practice_guard -q` → 38 passed。
- 未做：官方演练对照（步骤 F）；正式测试禁止。
