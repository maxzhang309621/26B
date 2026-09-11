# Q3/Q4 官方演练测评汇总（2026-09-11）

**提交/演练默认策略（当前代码）：**
- **Q3**：8×1200 + 讲义二测点 + 光学可行域网格  
- **Q4**：证书航路 **8×995+12×1865**（`runner_q4.run_q4`），有证明覆盖硬停  

每次汇报必含 **秒/源**。

---

## 当前对比基线

| 问题 | 策略 | 全清 | 均 VT (s) | 秒/源 | 证据 |
|------|------|------|-----------|--------|------|
| **Q3** | lecture-align 2238 | **5/5** | **4714** | **388** | `output/q3-results/official_lecture_align_20260911_2238_5.json` |
| **Q4** | cert 995+1865 | **5/5** | **8899** | **669** | `output/q4-results/official_cert_995_1865_20260911_2232_5.json` |

## 历史锁（对照）

| 问题 | 策略 | 全清 | 均 VT | 秒/源 | 证据 |
|------|------|------|-------|--------|------|
| Q3 | 18:24 Step7 | 5/5 | 5001 | 371 | `official_best_20260911_1824_5.json` |
| Q4 | v_nofar 12×2100 | 10/10 | 8508 | 677 | `overnight_v_nofar_10.json` |

---

## Q4 官方演练批次（按均 VT 排序）

| 策略 ID | 说明 | 全清 | 均 VT | 秒/源 | 批次文件 |
|---------|------|------|-------|-------|----------|
| **cert-995-1865** | **当前默认：8×995+12×1865** | **5/5** | **8899** | **669** | `official_cert_995_1865_20260911_2232_5.json` |
| **v_nofar** | 历史基线：12×2100 | **10/10** | **8508** | **677** | `overnight_v_nofar_10.json` |
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
| **当前最佳（18:24 五局）** | **5/5** | **5001** | **371** | `official_best_20260911_1824_5.json` |
| round3-q12（历史十局） | 10/10 | 5245 | 475 | `q3-batch-round3-q12-10.json` |
| q12 + locate 内核（早期） | 10/10 | 6257 | 460 | `q3-batch-q12-10.json` |

---

*仅演练数据；正式测试各 3 次，禁止自动触发。*
