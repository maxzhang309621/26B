# Q3/Q4 官方演练测评汇总（2026-09-11）

**提交/正式测试默认策略：`v_nofar`（固定 12×2100 覆盖航路）**  
代码入口：`runner_q4.run_q4()` → `HuntPolicy(q4_dynamic_outer=False, q4_profile="dynamic_pure")`  
实验升级：`runner_q4.run_q4_v2()`（动态外环 + v2 定位，仅 mock/消融用，**非**官方基线）

---

## 锁定基线（对比用）

| 问题 | 策略 | 全清 | 均 VT (s) | 秒/源* | 证据 |
|------|------|------|-----------|--------|------|
| **Q3** | round3-q12 | **10/10** | **5245** | **475** | `output/drill/q3-batch-round3-q12-10.json` |
| **Q4** | **v_nofar** | **10/10** | **8508** | **677** | `output/q4-results/overnight_v_nofar_10.json` |

\*秒/源 = 每局 `VT ÷ jammer_count` 再对 10 局取平均。

---

## Q4 官方演练批次（按均 VT 排序）

| 策略 ID | 说明 | 全清 | 均 VT | 秒/源 | 批次文件 |
|---------|------|------|-------|-------|----------|
| **v_nofar** | **基线：12×2100，跳过远二站** | **10/10** | **8508** | **677** | `overnight_v_nofar_10.json` |
| v_outer11_1900 | 外环 11×1900 | 9/10 | 8421 | 713 | `q4-batch-outer11-1900-10.json` |
| v_jung_nn | 外环 NN 排序 | 10/10 | 8553 | 678 | `overnight_v_jung_nn_10.json` |
| v_fan18m4 | miss≥4 跳过 18m 扇形 | 10/10 | 9138 | 683 | `overnight_v_fan18m4_10.json` |
| v_outer11_1900_q12 | outer11 + Q1/Q2 定位核 | 10/10 | 9140 | 756 | `q4-batch-outer11-q12-10.json` |
| dynamic_v2_dir8 | 动态外环 v2（接线正确） | 10/10 | 9371 | 749 | `q4-batch-v2-dir8-official.json` |
| dynamic_v2_miswired | 动态 v2（drill 误走默认 v2 早期） | 10/10 | 10098 | 737 | `q4-batch-v2-miswired.json` |

完整 overnight 消融列表见 `output/drill/overnight_q4_state.json`。

---

## Q4 代码升级（已合入，默认仍 v_nofar）

| 模块 | 升级内容 |
|------|----------|
| `coverage.pick_q4_outer_ring` | 定向≥8 → 12×2100；否则 11×1900；0 定向跳过外环 |
| `policy` | `v2` 定位 + `dynamic_pure`（v_nofar）双 profile；Q4 fill unheard |
| `drill_io` | 演练经 `runner_q4.run_q4()`，不再绕过 runner |
| `run_q4_practice_batch` | UI/result 预读 omni/dir 供动态外环（v2 实验用） |
| `q4_benchmark` | mock 对比 fixed vs dynamic |

**注意：** 官方 `/enter` 演练窗通常读不到 omni/dir，动态 v2 在官方上会退化为保守 12×2100；实测 v2 批次均 VT **9371 s**，慢于 v_nofar **8508 s**。故**提交与正式测试保持 v_nofar**。

---

## Q3 参考

| 策略 | 全清 | 均 VT | 秒/源 | 批次文件 |
|------|------|-------|-------|----------|
| round3-q12（基线） | 10/10 | 5245 | 475 | `q3-batch-round3-q12-10.json` |
| q12 + locate 内核（早期） | 10/10 | 6257 | 460 | `q3-batch-q12-10.json` |

---

*仅演练数据；正式测试各 3 次，禁止自动触发。*
