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

## T12–T17 运行数据反演验证（2026-09-11）

- 文件：`src/log_parse.py`、`src/inversion.py`、`src/validation.py`、`src/viz_inversion.py`、`src/invert_cli.py`、`src/tests/test_inversion.py`
- 反演复用 `intersect_cones` / `locate_quality`（半宽 1.01°），点估计为 Welzl 包围圆心；不写回策略。
- 残差门禁用 ±1.01°（赛题 ±1° + `svd_deg` 两位小数舍入）。
- 冒烟：
  - `python -m unittest tests.test_inversion -q` → 9 passed（含空日志、缺文件、无误差两站、Q3 seed0 包含率=1）
  - `python invert_cli.py --mock`：三局包含率=1、残差带通过；均误差约 7.6–10.2 m；图写入 `output/inversion/`
  - `python invert_cli.py --drill ../output/drill/p3-20260911-144700.json`：20 频道一致性报告，未崩溃

## T18–T24 问题 4 路径时效（2026-09-11）

- 文件：`src/policy.py`、`src/coverage.py`、`src/belief.py`、`src/runner_q4.py`、`src/q4_benchmark.py`、`src/tests/test_q4.py`、`src/tests/test_q3_cost_ledger.py`
- **T18 台账**：定向模式也计算 `backbone_planned_s` / `rejoin_s`；三档加和 = `travel_s`。
- **T19 延后**：`q4_path_profile="pathopt"` 在覆盖期只清「当前听点新听源」以及增量代价 ≤ 400 m 的 pending；其余覆盖结束后再清。`run_q4()` 仍为 `v_nofar` 听完即清。
- **T20/T21 扇区锯齿与贪心跳点**：mock 漏清或行驶变差，**未接入默认 pathopt**。听点几何仍是 900/1200/2100 双环最近邻。`sector_fused_order` / `open_path_order` / `hypothesis_hits` 保留备用。
- **T23**：`directional_front_cover_ok(dense=...)`。
- **T24**：`run_q4_pathopt()`；benchmark 接受 `q4_outer_mode` 与 `--profile pathopt`。
- 冒烟：
  - `python -m unittest discover -s tests -q` → **91 passed**
  - mock 24 种子：pathopt **miss=0**；均 VT **7561 vs 7769**（v_nofar）；均行驶 **6179 vs 6393**
- 未做：官方演练对照；正式测试禁止。默认提交入口仍是 `run_q4()` = `v_nofar`。

## 交错巡游 + 搜到即清对照（2026-09-11）

- 按用户要求撤回「搜完再清」。`run_q4_pathopt()` 仅把听点序改为 `sector_fused_order`，每听点后仍 `_drain_pending()`，定位核与 `v_nofar` 相同。
- 冒烟：`python -m unittest discover -s tests -q` → **95 passed**
- mock-24：交错 **miss=0**，均 VT **8592** / 均行驶 **7150**；`v_nofar` 均 VT **7769** / 均行驶 **6393**
- 结论：内外交错在搜到即清下**没有**优于双环最近邻，径向折返增加约 11% 行驶。默认入口不切换。

## T25–T27 交错搜索 + 先搜后清（2026-09-11）

- 文件：`src/policy.py`、`src/coverage.py`、`src/runner_q4.py`、`src/tests/test_q4.py`
- **T25**：pathopt 覆盖走 `sector_fused_order`；除 `near` 外覆盖期不 `/clear`。
- **T26**：覆盖结束后 `open_path_order` 按预测矩形代表点批量清除；交会过大时扇形补清，再专用第二站。
- **T27**：`run_q4()` 仍为 v_nofar。
- 冒烟：
  - `python -m unittest discover -s tests -q` → **95 passed**
  - mock-24：pathopt **miss=0**；均 VT **8578** / 均行驶 **6680**；对照 v_nofar 均 VT **7769** / 均行驶 **6393**（行驶未优于基线，默认入口不切换）
- 未做：官方演练；正式测试禁止。
- **已撤回**：用户改回搜到即清；上表仅作历史记录。当前 `run_q4_pathopt()` 见「交错巡游 + 搜到即清对照」。

## T28–T29 问题 3 滚动时域清除（2026-09-11）

- 文件：`src/coverage.py`、`src/policy.py`、`src/runner_q3.py`、`src/tests/test_q3.py`、`src/figures/fig_q3_path_gif.py`
- **T28**：`_batch_clear_by_path` 改为每步 `open_path_channel_order` 重解；远第二站按 ~280 m 前缀 `/measure`；滞回 50 m。
- **T29**：`run_q3()` 不变。GIF 对照现行 vs RH 批量。
- 冒烟：`python -m unittest discover -s tests -q` → **101 passed**；mock-8 均 ΔVT −508 s（相对 `run_q3`）。
- 未做：未改 `run_q3()` 默认入口；正式测试禁止。

## T30–T32 问题 4 定向测向定位修正器（2026-09-12）

- 文件：`src/dir_corrector.py`、`src/policy.py`、`src/runner_q4.py`、`src/tests/test_dir_corrector.py`
- **T30**：`heading_feasible`（听到 ⇒ 1500 m 前瓣；听不到 ⇒ 仅 1000 m 挖朝向）、`heard_region`、`locate_quality_dir`（过收缩 / SEC 变大回退问题一核）、`next_station_dir`
- **T31**：仅 hexbatch 走 `_channel_locate_quality`；`use_dir_corrector=False` 复现旧轨迹；统计 `dir_corrector` / `corrector_used` / `corrector_fallback`
- **T32**：包含率、背面无信号、单站回退、Q4 mock 全清；Q3 不改 `locate_quality`
- 冒烟：`python -m unittest discover -s tests -q` → **147 passed**
- 对照（重建 Source）：seed 3/4/0/5 开关 VT 打平，全清，`corrector_fallback=0`
- 未做：官方演练；正式测试禁止；尚未把 \(R^\ast\) 变成更近的第二站以压时间



