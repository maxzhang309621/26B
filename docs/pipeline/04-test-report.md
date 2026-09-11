# 系统测试报告

- 项目：2026 B 题无线电干扰源定位与清除
- 范围：架构 v1.2 步骤 G–L（运行数据反演验证）
- 日期：2026-09-11
- 结论：**系统测试通过**

## 验收对照（v1.2）

| 步骤 | 用例类型 | 做法 | 结果 |
|------|----------|------|------|
| G | 正常 | 两站 `direction` 抽出坐标与示向 | 通过 |
| G | 边界 | 空日志 → 空 dict | 通过 |
| G | 异常 | `accepted=false` 被忽略；缺文件 `FileNotFoundError` | 通过 |
| H | 正常 | 无误差两站：真值在可行域内，圆心距 < 直径 | 通过 |
| I | 正常 | mock Q3 seed0/1、Q4 seed3：包含率=1；残差在 ±1.01° | 通过 |
| J | 正常 | 读 `output/drill/p3-20260911-144700.json`，20 频道，模式标明仅一致性 | 通过 |
| K | 正常 | 四类 PNG 轴带单位 (m)/(deg) | 通过 |
| L | 正常 | `--mock` / `--drill` 入口跑通 | 通过 |

## 回归

```
cd src
python -m unittest tests.test_inversion tests.test_geometry tests.test_protocol tests.test_q3 tests.test_q4 tests.test_candidate tests.test_practice_guard -q
```

**46 passed**（约 0.66 s）。未跑官方演练，未开正式测试。

## mock 定量（有真值）

| 场景 | 包含率 | ±1° 带（含舍入） | 均定位误差 |
|------|--------|------------------|------------|
| q3-seed0-n10 | 1.0 | 1.0 | 10.23 m |
| q3-seed1-n12 | 1.0 | 1.0 | 8.70 m |
| q4-seed3-n12-nd4 | 1.0 | 1.0 | 7.56 m |

产物：`output/inversion/mock_summary.json`、`drill_summary.json` 及 PNG 图。

## 问题分流

（v1.2 无开放缺陷。）

---

# 系统测试报告（v1.3 路径时效）

- 项目：2026 B 题无线电干扰源定位与清除
- 范围：架构 v1.3 步骤 M–T（问题 4 行驶时间 / 路径）
- 日期：2026-09-11
- 结论：**系统测试通过（mock）**；官方演练未跑；正式测试禁止。

## 验收对照（v1.3）

| 步骤 | 用例类型 | 做法 | 结果 |
|------|----------|------|------|
| M | 正常 | Q4 mock 台账三档加和 = travel；planned+rejoin=backbone | 通过 |
| N | 正常 | pathopt 混合源全清；远 pending 覆盖期不强制清 | 通过 |
| N | 边界 | 近心朝外仍全清 | 通过 |
| P/Q | 异常回退 | 扇区锯齿 / 贪心跳点 mock 漏清，默认 pathopt 不用 | 已记录 |
| R | 正常 | `open_path_order` 5 点置换唯一且走遍 | 通过 |
| S | 正常 | `directional_front_cover_ok()` 默认 True；dense 旗标可调用 | 通过 |
| T | 正常 | mock 24 种子 pathopt miss=0，均行驶/均 VT 低于 `run_q4()` | 通过 |
| 回归 | 正常 | `v_nofar` `test_cover_inner_before_outer` 仍约束 `run_q4()` | 通过 |

## 回归

```
cd src
python -m unittest discover -s tests -q
```

**91 passed**（约 9 s）。未跑官方演练，未开正式测试。

## mock 定量（24 种子，同一 `_mix_sources`）

| 策略 | miss | 均 VT (s) | 均行驶 (s) |
|------|------|-----------|------------|
| `run_q4()` v_nofar | 0 | 7768.7 | 6392.9 |
| `run_q4_pathopt()` | 0 | 7561.5 | 6179.0 |

Δ mean VT ≈ **−207 s**；Δ mean travel ≈ **−214 s**。未达 5000 s 目标（架构已声明非门禁）。

## 问题分流

无 L1 开放缺陷。扇区融合未达验收，已按候选回退，不升级 L2。


## 问题分流

无失败项。L1/L2/L3 未触发。

## 备注

- `svd_deg` 四舍五入到两位小数后，残差可略超 1.000°；门禁与几何核一致取 1.01°。
- 反演未接入 `HuntPolicy`。
