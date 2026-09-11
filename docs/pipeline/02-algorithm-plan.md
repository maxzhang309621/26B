# 算法方案：2026 B 题无线电干扰源的快速自动定位与清除

> 依据已确认架构 `01-architecture.md` v1。复杂步骤给出优先级候选，供调试回退。

## 步骤 1：问题 1 几何核

- 选定算法：
  1. **角扇 → 半平面**：示向度 \(\theta\pm1^\circ\) 写成两条有向边界的闭半平面（二维叉积），不含对顶 2° 扇。
  2. **半平面交（首选）**：边界直线两两求交，保留满足全部半平面的顶点，再按极角排序得凸多边形。测点很少（\(n\le 20\)，至多 40 条半平面），\(O(n^2)\) 足够且易证空集/无界。
  3. **直径（首选）**：凸多边形顶点对枚举。顶点极少时与旋转卡壳同结果。
  4. **最小包围圆（首选）**：Welzl 随机增量（期望线性）；实现为迭代/浅递归（点数 ≤ 数十）。
  5. **直径圆覆盖**：比较 \(R_{\mathrm{sec}}\) 与 \(d/2\)；论文引用荣格定理 \(R\le d/\sqrt{3}\)，等边三角形取等。
- 选型理由：赛题 \(n\) 极小，优先正确、可证明、无重依赖。半平面交的经典最优算法是 Preparata–Shamos 分治 \(O(n\log n)\)，此处无性能压力。Welzl 有公开伪代码，避免引入 GPL/LGPL 整库。
- 候选：半平面交失败或数值不稳 → Shapely 大矩形裁剪角扇；直径 → 旋转卡壳；包围圆 → 钝角/锐角分类的三角形外接圆 + 直径圆（至多 3 点决定）。
- 参考资料：
  - Shamos, Hoey. *Geometric Intersection Problems*. FOCS 1976. https://euro.ecom.cmu.edu/people/faculty/mshamos/1976GeometricIntersection.pdf
  - 半平面交讲义：https://www.cs.umd.edu/class/fall2023/cmsc754/Lects/lect06-duality.pdf
  - Welzl. *Smallest Enclosing Disks (Balls and Ellipsoids)*. LNCS 555, 1991. https://www.ibr.cs.tu-bs.de/courses/ws2122/ag/otherstuff/smallest-disk-welzl.pdf
  - 旋转卡壳：Shamos 1978；Toussaint 1983；https://en.wikipedia.org/wiki/Rotating_calipers
  - Jung, H. (1901). *Über die kleinste Kugel…*；平面形式 \(r\le d/\sqrt{3}\)：https://en.wikipedia.org/wiki/Jung%27s_theorem
- 接口约定：`intersect_cones(stations, bearings_deg, delta_deg=1.0) -> Polygon | Unbounded | Empty`；`diameter(poly) -> float`；`smallest_enclosing_circle(points) -> (cx,cy,r)`；`diameter_circle_covers(poly) -> bool`。
- 依赖：Python 3.10+ 标准库 `math`；测试可用 `unittest`。

## 步骤 2：协议客户端与附件计时

- 选定算法：**同步请求-响应 + 幂等键**。与附件 2 示例一致，用标准库 `urllib.request` POST JSON；每个新动作新 `request_id`；超时/断线重试必须复用原 body 与原 ID；串行等待；同时检查 HTTP 状态与 `accepted`。
- 选型理由：附件官方示例即此模式，无额外依赖；`requests` 非必要。
- 参考资料：`26B/data/` 附件 1、2；摘录 `26B/doc/simulator-protocol-extract.txt`。
- 接口约定：`RobotClient.enter/measure/clear/exit`；内存维护 `position`、`channel`、`virtual_time_s`（仅 `accepted=true` 更新）；动作日志列表。进程内可注入 `transport`，官方走 HTTP，mock 走函数调用。
- 依赖：标准库 `json`、`urllib.request`、`uuid`。

## 步骤 3：本地物理仿真 `mock_sim`

- 选定算法：**离散事件 / 逐步推进**，与附件同一套耗时公式。每源：位置、频道、\(r_{\mathrm{eff}}\)、可选定向角。示向度 = 真方位 + 该检测点固定误差 \(\varepsilon(S)\in[-1,1]\)（由位置哈希或预生成，同点不变）。
- 选型理由：必须能复现附件表 2 的 105/111/194/199 s，并支持无官方模拟器的策略回归。
- 参考资料：附件 1 表 1–2；附件 2 第 2、4、10 节。
- 接口约定：与 `RobotClient` 相同的 dict 响应（`accepted`、`measure_result`、`svd_deg`、`clear_result`、`virtual_time_s`）。
- 依赖：标准库。

## 步骤 4：问题 2 候选区与推荐点

- 选定算法（首选）：**AOA 正交配置**。名义源 \(\hat G=S_1+\hat\rho u(\theta)\)，第二点 \(\hat G\pm h n\)，\(h=600\,\mathrm{m}\)（对名义源 \(\beta=90^\circ\)）。候选区为最坏交会直径水平集的矩形内近似：随体坐标 \(x\in[400,1300]\)，\(|y|\in[400,800]\)，再与 \(|P|\le 1800\)、可听盘求交。质量指标用交会平行四边形面积 \(A\propto \rho_1\rho_2/|\sin\beta|\)。
- 选型理由：两站 AOA 的 Fisher 信息 / GDOP 在交角 90° 最好；沿示向线 \(\sin\beta\to 0\)。文献给出固定距离下最优角间隔，本问题距离未知，故用名义距离 + 侧向带。
- 候选：网格上最小化最坏直径 \(Q(P)\)；第三测点沿定位区长轴法向。
- 参考资料：
  - Doğançay, Hmam. *Optimal angular sensor separation for AOA localization*. Signal Processing 88 (2008) 1248–1260. https://ui.adsabs.harvard.edu/abs/2008SigPr..88.1248D/abstract
  - *Effect of an Additional Sensor on AOA Localization Performance*. EUSIPCO 2008. https://www.eurasip.org/Proceedings/Eusipco/Eusipco2008/papers/1569101826.pdf
  - GDOP 图示（正交好、共线差）：IEEE Access 2020. https://doi.org/10.1109/access.2020.3033281
- 接口约定：`candidate_region(s1, theta_deg) -> list[Polygon]`；`recommend_second(s1, theta_deg, now=None) -> (x,y)`。
- 依赖：步骤 1 几何核。

## 步骤 5：问题 3 全向策略

- 选定算法：
  1. **听全覆盖（首选）**：等圆覆盖圆盘。目标半径 1800、覆盖半径按最坏 1000。单位圆上 \(r(7)=1/2\) 已小于 \(1000/1800\approx 0.556\)，故 **1 中心 + 环上点** 足够。实现取原点 + 8 个环点（半径 1200 m，间隔 45°），用边界采样验证每个 \(|x|=1800\) 的点到最近航路点 ≤1000；若不满足则加密到 10 点或把环半径调到 1200–1300。
  2. **路径**：航路点凸位置，从原点出发环向走一圈（直线段），属覆盖路径规划中的同心环/分解后沿细胞边界，不是栅格割草机。
  3. **频道**：原点 1→20 全扫；之后只扫未发现频道；定位某源时保持该频道直至清除。
  4. **插入**：听到则中断覆盖，按步骤 4 去 \(S_2\)，交会后若 \(R_{\mathrm{sec}}>20\) 再取第三点，然后 `/clear` 圆心；多个待清源取最近 \(S_2\)。
  5. **停止**：清除数达 16，或覆盖计划完成。
- 选型理由：Kershner/Friedman 等圆覆盖给出 7 盘理论保证；8 环点留余量。CPP 综述表明无障碍圆域用规则分解即可，不必 Morse 复杂分解。
- 候选：环上 6 点半径 1200；失败则加密环或加第二环（ρ=800 与 1400）。
- 参考资料：
  - Disk covering problem；\(r(7)=1/2\)：https://en.wikipedia.org/wiki/Disk_covering_problem
  - Kershner, R. (1939). *The number of circles covering a set*.
  - Friedman. *Circles Covering Circles*.
  - Galceran, Carreras. *A survey on coverage path planning for robotics*. RAS 2013. https://doi.org/10.1016/j.robot.2013.09.004
- 接口约定：`omni_waypoints() -> list[(x,y)]`；`run_q3(env) -> stats`。
- 依赖：步骤 1–4。

## 步骤 6：问题 4 定向策略

- 选定算法（首选）：问题 3 的内覆盖 **加上圆外环**（半径约 2200 m，8–12 点），保证朝外 180° 半平面内必有测点。信念：`no_signal` 只从可行集挖掉「以测点为中心、半径 1000、且相对测点张角覆盖该半平面」的区域，不把频道标成全局不存在。第二点必须落在第一次可见半平面内。
- 选型理由：定向有效区是半平面，圆内测点无法看见朝外源；附件允许出圆。艺术画廊式「从多方向看见」在此退化为外环采样。
- 候选：沿大圆外侧做更密的圆周巡逻（间隔 < 有效半径在圆周上的弦）。
- 参考资料：附件 2 §2.2；半平面可见性；CPP 综述中的边界跟随作为外环实现。
- 接口约定：`directional_waypoints() -> list[(x,y)]`；`run_q4(env) -> stats`。
- 依赖：步骤 5。

## 步骤 7：可视化

- 选定算法：Matplotlib 静态图（交会四边形、候选带、航路）。与 25B 一致，便于论文插图。
- 参考资料：项目内 25B `plotting` 风格（轴标签、单位、无装饰渐变）。
- 依赖：`matplotlib>=3.7`。

## 步骤 8–9：官方演练与正式测试

- 选定算法：同一 `runner`，`transport=HTTP`。不改策略。人工启动模拟器、登录、倒计时结束后再 `enter`。用 `remaining_real_duration_s` 看门。
- 参考资料：附件 1 §4；附件 2 §12。
- 依赖：本机模拟器、参赛队号（环境变量 `CUMCM_ROBOT_ID`）。

## 候选尝试记录

| 步骤 | 候选算法 | 状态 | 失败原因 |
|------|----------|------|----------|
| 1 | 两两求交 + 顶点过滤 | 未试 | |
| 1 | Shapely 裁剪 | 未试 | |
| 1 | Welzl 包围圆 | 未试 | |
| 4 | 名义正交 \(h=600\) | 未试 | |
| 4 | 网格最坏直径 | 未试 | |
| 5 | 原点+8×1200 m | 未试 | |
| 5 | 原点+6×1200 m | 未试 | |
| 6 | 内覆盖+外环 2200 m | 未试 | |

## 依赖汇总

| 包 | 版本 | 用途 |
|---|---|---|
| Python | ≥3.10 | 运行时 |
| matplotlib | ≥3.7 | 步骤 7 |
| numpy | ≥1.24（可选） | 网格采样；几何核可不依赖 |

禁止引入 GPL 几何库作为必选依赖。官方 HTTP 仅标准库。

## 任务分配

| 任务 ID | 实现内容 | 关联步骤 | 参考资料 |
|---------|----------|----------|----------|
| T1 | `geometry.py`：角扇半平面、求交、直径、Welzl、覆盖判定；`tests/test_geometry.py` | 1 | Welzl 1991；Jung；Shamos 1976 |
| T2 | `robot_client.py` + `mock_sim.py`；复现附件计时示例；`tests/test_protocol.py` | 2–3 | 附件 1 表 2、附件 2 §10 |
| T3 | `candidate.py` 候选区与推荐第二点；`tests/test_candidate.py` | 4 | Doğançay 2008 |
| T4 | `coverage.py` 全向航路点及覆盖验证 | 5 | Disk covering；Kershner 1939 |
| T5 | `belief.py` + `policy.py` + `runner_q3.py`；mock 上多种子清除比例=1 | 5 | Galceran 2013 |
| T6 | 圆外航路 + `runner_q4.py`；含朝外定向源的 mock 场景 | 6 | 附件 2 §2.2 |
| T7 | `viz.py`、`q1_cli.py`；交会/候选/航路图 | 1,4,7 | 架构可视化约定 |
| T8 | HTTP 传输、配置、动作日志导出（正式测试用） | 8–9 | 附件 2 §12 |

实现顺序：T1 → T2 → T3 → T4 → T5 → T6 / T7（可并行）→ T8。

## 变更 v1.1（步骤 A–F）

- **A 问题 1 质量**：`locate_quality` = 半平面交 + Welzl + 近共线检测（\(|\sin\beta|<0.08\)）；`can_clear_20` 只用包围圆半径，角扇余量 1.01°。
- **B 无信号裁剪**：包围圆圆心落在某 `no_signal` 点 1000 m 内则禁止清除、要求再测。
- **C 问题 2 下一站**：`next_stations`；全向保留正交推荐；定向只用前瓣兼容的近侧点，可返回空列表。
- **D/E 接线**：`HuntPolicy._localize_and_clear` / `_take_second_fix` 只走上述接口。
- **F 演练**：本任务只做 mock/单测；演练另开，禁止正式测试。

| 任务 ID | 实现内容 | 关联步骤 |
|---------|----------|----------|
| T9 | `locate_quality` + 单测 | A, B |
| T10 | `next_stations` / `front_compatible` + 单测 | C |
| T11 | `policy` 接线 + Q3/Q4 mock 回归 | D, E |

## 变更 v1.2（步骤 G–L：运行数据反演验证）

依据已确认架构 `01-architecture.md` v1.2。赛题示向误差为**有界闭区间 ±1°**（非高斯），因此不采用需要噪声方差的 LS/ML/CRLB 作为主验证；那些方法作候选对照，不进默认路径。

### 步骤 G：日志解析

- 选定算法：**按频道分组的事件流解析**。遍历 `path`/`request`/`response`；仅 `accepted=true`；`/measure` 的 `direction` 记测站与 `svd_deg`，`no_signal` 记静默点，`near` 记近距点；`/clear` 记清除点与成败。
- 选型理由：与附件 2 字段及现有 `RobotClient.log` / `output/drill/*.json` 一致，无额外依赖。
- 参考资料：附件 2 协议；现仓库 `src/robot_client.py`、`output/drill/p3-*.json`。
- 接口约定：`parse_action_log(log) -> dict[int, ChannelObs]`；`parse_drill_file(path) -> dict[int, ChannelObs]`。
- 依赖：标准库。

### 步骤 H：单频道反演

- 选定算法（首选）：
  1. **可行域**：`intersect_cones` / `locate_quality`，半宽 **1.01°**（与策略舍入余量一致）。
  2. **点估计**：有界凸可行域顶点的 **Welzl 最小包围圆心**（1-center / 最小最大误差点）。有界误差 AOA 下，真值落在半平面交多面体，包围圆心是与策略清除点同一口径的代表点。
- 选型理由：与问题 1/3/4 几何核同一公式，避免「论文一套、策略一套」。测站极少，不必 PLS/Stansfield 迭代。
- 候选（仅当包围圆心系统偏离真值且包含性仍过时再试）：伪线性最小二乘（Brown DWLS / PLS）；两两示向线交点加权（Fusion 2014 weighted intersections）。**默认不实现。**
- 参考资料：
  - Welzl 1991 最小包围圆（步骤 1 已采用）
  - Bishop, Jensfelt et al. *Characterizing the Worst-Case Position Error in Bearing-Only Target Localization*. https://publications.lib.chalmers.se/publication/218784
  - Doğançay, Hmam. *Optimal angular sensor separation for AOA localization*. Signal Processing 88 (2008).
  - 候选：`Performance Analysis of AOA-Based Localization Using the LS Approach` (2020) https://doi.org/10.1155/2020/9346142
- 接口约定：`invert_channel(obs, delta_deg=1.01) -> InvertResult`（region、point_est=sec_center、sec_r、can_clear_20）。
- 依赖：现有 `geometry.py`。

### 步骤 I：有真值批量验证

- 选定算法：**集合包含检验 + 圆周残差**。
  - 包含：真源必须落在全部 `direction` 测站的闭角扇交内（半平面 `contains`，不依赖裁剪框顶点）。
  - 残差：\(\tilde\theta = \mathrm{wrap}(\theta_{\mathrm{true}}-\mathrm{svd})\)，应落在 \(\pm 1^\circ\)（mock 生成规则）。
  - 定位误差：\(\| \hat G - G \|_2\)；清除距离：成功 `/clear` 点到真源。
- 选型理由：赛题误差模型是有界而非高斯；包含性是模型正确的充分可测条件。Monte Carlo RMSE 闭合式（LS-MSE 2020）需要 \(\sigma_\theta\)，与 ±1° 闭区间不符，不作门禁。
- 接口约定：`validate_with_truth(result, obs, source_xy) -> TruthMetrics`；`containment_rate(rows) -> float`。
- 批量：mock 全向种子 `(0,10),(1,12)` + 定向混合 `(3,12,4)`；有效 `direction≥2` 的频道包含率必须为 1。
- 依赖：`mock_sim` + `runner_q3` / `runner_q4`。

### 步骤 J：无真值一致性

- 选定算法：**自洽残差**。用点估计反推各站示向，与测量差的绝对值；以及 `can_clear_20` 与最后一次 `clear_ok` 是否同号。标题必须标明「仅一致性，非定位精度」。
- 选型理由：官方演练不给坐标，不能报 RMSE。
- 接口约定：`validate_consistency(result, obs) -> ConsistMetrics`。
- 依赖：步骤 G–H。

### 步骤 K：可视化

- 选定算法：Matplotlib 静态图（与步骤 7 / 25B 一致）：(1) 单频道交会叠真值与测站示向；(2) 估计 vs 真值散点（等比例 + y=x）；(3) 定位误差直方图（m）；(4) 示向残差直方图（deg）。
- 参考资料：项目 `src/viz.py`。
- 依赖：`matplotlib>=3.7`。

### 步骤 L：CLI

- 选定算法：批处理入口。`--mock` 跑有真值批次并出图；`--drill FILE` 只跑一致性（缺真值不崩溃）。输出 `output/inversion/`。
- 依赖：标准库 argparse。

### 候选尝试记录（v1.2）

| 步骤 | 候选算法 | 状态 | 失败原因 |
|------|----------|------|----------|
| H | Welzl 包围圆心 | 采用 | |
| H | 伪线性 LS / DWLS | 未试 | 默认不需要 |
| H | 两两交点加权 | 未试 | 默认不需要 |
| I | 有界角扇包含 + wrap 残差 | 采用 | |
| I | 高斯 CRLB / 解析 MSE | 未采用 | 与 ±1° 闭区间误差模型不符 |

| 任务 ID | 实现内容 | 关联步骤 | 参考资料 |
|---------|----------|----------|----------|
| T12 | `log_parse.py` + 单测 | G | 附件 2；drill JSON |
| T13 | `inversion.py` 复用几何核 + 单测（无误差两站） | H | Welzl；Bishop 最坏定位误差 |
| T14 | `validation.py` 包含/残差；mock 多种子包含率=1 | I | 赛题 ±1°；mock `_site_error_deg` |
| T15 | 无真值一致性 + 读 drill JSON | J | 架构 v1.2 步骤 J |
| T16 | `viz_inversion.py` 四类图 | K | `src/viz.py` |
| T17 | `invert_cli.py` 一键跑 + 冒烟 | L | 输出目录约定 |

实现顺序：T12 → T13 → T14 → T15 / T16（可并行）→ T17。

---

## 变更 v1.3（步骤 M–T：问题 4 路径时效）

依据已确认架构 `01-architecture.md` v1.3。默认提交入口 `run_q4()` 保持 `v_nofar`；新逻辑走 `run_q4_pathopt()` / `q4_path_profile="pathopt"`。禁止引入新运行时依赖。禁止正式测试。

### 步骤 M：问题 4 行驶台账

- 选定算法：**路径段事件归因**（与问题 3 `_move_decomposition` 同一口径）。覆盖听点上的 `/measure` 记 `backbone`；定位 `/measure` 记 `service`；`/clear` 记清除绕行。计划折线 = 按首次到达顺序的互异主干听点折线长 / 5 m/s；`rejoin_s = backbone_scan_s - planned_s`（问题 4 不再恒为 0）。
- 选型理由：问题 3 已实现且有单测；Galceran 综述把覆盖行驶与细胞间转移分开记账。不必上轨迹联合分布（PACE/VLDB）——本赛虚拟时间是确定直线 5 m/s。
- 候选：离线重放 drill JSON 的折线归因（仅诊断，不进策略）。
- 参考资料：
  - Galceran, Carreras. *A survey on coverage path planning for robotics*. RAS 2013. https://doi.org/10.1016/j.robot.2013.09.004
  - 本仓库 `policy._move_decomposition`、`tests/test_q3_cost_ledger.py`
- 接口约定：`HuntPolicy._move_decomposition()` 在 `directional=True` 时也填 `backbone_planned_s` / `backbone_rejoin_s`；`backbone_scan_s + localization_s + clear_detour_s = travel_s`（允许 1e-6）。
- 依赖：无新库。

### 步骤 N：覆盖/清除相位分离（延后服务）

- 选定算法（首选）：**最便宜插入的增量绕行代价**（Rosenkrantz–Stearns–Lewis cheapest insertion，2-近似）。对每个 pending 源，代价 \(\Delta = \|now-C\|+\|C-rejoin\|-\|now-rejoin\|\)（即现有 `_incremental_service_cost`）。若 \(\Delta \le \Delta_{\max}\)（默认 80 m，约 16 s）则插入清除；否则延后到覆盖结束。覆盖结束后对剩余 pending 做一次批量清除。`near` 仍当场 `/clear`。停搜定义不变：`heard = cleared + pending`。
- 选型理由：问题 4 当前每个听点后立刻 `_drain_pending()`，且 `test_directional_q4_never_uses_route_deferral` 禁止延后——这是慢局折返的主因。问题 3 已有同一公式与 step8 边插入。Vansteenwegen TOPTW 的 score²/Shift 插入过重（本问题每个已听源最终都要清，不是选子集得分）。
- 候选：
  1. 严格两阶段（覆盖期 \(\Delta_{\max}=0\)，全部延后）——若插入阈值调参不稳则回退。
  2. Vansteenwegen ILS 插入（TOPTW）——点数多且要摇动时再试。
- 参考资料：
  - Rosenkrantz, Stearns, Lewis. *An Analysis of Several Heuristics for the Traveling Salesman Problem*. SIAM J. Comput. 6(3), 1977. https://doi.org/10.1137/0206041
  - Vansteenwegen et al. *Iterated local search for the team orienteering problem with time windows*. https://lirias.kuleuven.be/retrieve/91f75023-e620-4f54-90c2-5ada4495c62c
  - 本仓库 `_incremental_service_cost`、`_step8_insert_delta`
- 接口约定：`HuntPolicy(..., q4_path_profile="pathopt")` 启用延后；`q4_insert_delta_max_m` 默认 80。`run_q4()` 不改变该行为。
- 依赖：现有 `policy.py`。

### 步骤 P：扇区融合巡游

- 选定算法（首选）：**极角 Morse / 径向细胞分解后的扇区锯齿巡游**（Acar et al. 2002：Morse 函数取 \(\mathrm{atan2}\)，切片为射线）。听点集仍用现有 `q4_listen_set`（原点 + 8×900 + 8×1200 + 12×2100），**不改点、改访问拓扑**。将非原点听点按 30° 扇区分箱（12 箱对齐外环）；偶数箱按半径升序，奇数箱按半径降序；箱与箱在当前半径上短弧衔接。原点仍先全扫。
- 选型理由：现拓扑是两个同心环串行，主干下界约 4500 s。极角分解把 900/1200/2100 合成同一扇区的进出，避免先付内环整圈再付外环整圈。保持原点集则定向覆盖证书与近心朝外能力不丢。Morse 径向切片比螺旋（Bosse）更贴合「途听必须在射线上」的 900 m 约束。
- 候选：
  1. 阿基米德螺旋（Galceran 综述引用 Bosse 2007）——若锯齿在 mock 上因过多径向折返变差再试。
  2. 12 辐条各含 900/1200/2100（加密内环到 12 点）——仅当现 8 内环角与 12 外环角错位导致锯齿空驶时再试。
- 参考资料：
  - Acar, Choset, Rizzi, et al. *Morse Decompositions for Coverage Tasks*. IJRR 21(4) 2002. http://biorobotics.ri.cmu.edu/papers/paperUploads/A028807.pdf
  - Galceran, Carreras. RAS 2013 CPP survey. https://doi.org/10.1016/j.robot.2013.09.004
- 接口约定：`coverage.sector_fused_order(waypoints) -> list[Point]`；`HuntPolicy._run_pathopt_cover()` 按该序访问；`test_cover_inner_before_outer` 仅约束 `v_nofar`。
- 依赖：标准库 `math`。

### 步骤 Q：剩余位姿的在线探针选择（减点）

- 选定算法（首选）：**加权贪心集合覆盖**（Chvátal 1979 / Hochbaum）：元素 = 剩余未知信道的离散位姿假设（复用 `belief.might_hear` 的场采样 × 24 朝向）；集合 = 尚未访问的覆盖听点。反复选 \(p^*=\arg\max |新覆盖假设| / (d(now,p)+\varepsilon)\)，从当前位置出发，直到假设空或无有用探针。这是**选子集**，不是给固定 12 点排序。
- 选型理由：架构明确禁止重试已失败的「固定 12 点信息增益序」。Alon et al. 在线集合覆盖（权值倍增 / WINNOW）实现重且本问题假设集在每次测量后整批更新，离线贪心更贴切。`might_hear` 已具备假设采样，边际覆盖可直接计数。
- 候选：
  1. 次模 next-best-view（Lauri et al. 2020 matroid 贪心）——若信道间假设重叠导致贪心过早停再试。
  2. Alon–Awerbuch–Azar 在线集合覆盖 —— 候选耗尽时再上。
- **不要用**：Vander Hook cautious greedy（那是已知目标的主动定位，错层）。
- 参考资料：
  - Chvátal. *A Greedy Heuristic for the Set-Covering Problem*. MOR 1979. https://doi.org/10.1287/moor.4.3.233
  - Alon, Awerbuch, Azar, Buchbinder, Naor. *The Online Set Cover Problem*. STOC 2003. https://www.cs.tau.ac.il/~nogaa/PDFS/aaabnproc2.pdf
  - Lauri et al. *Multi-Sensor Next-Best-View Planning as Matroid-Constrained Submodular Maximization*. arXiv:2007.02084. https://ar5iv.labs.arxiv.org/html/2007.02084
  - 本仓库 `belief.ChannelBook.might_hear`
- 接口约定：`belief.uncovered_pose_count(ch, probe, scans) -> int`（或在 policy 内用 `might_hear` 的采样循环计数）；`HuntPolicy._pick_next_cover_wp(candidates) -> Point | None`。pathopt 外环/剩余点走此选择；`v_nofar` 仍最近邻。
- 依赖：现有 `belief.py` 采样网格。

### 步骤 R：剩余探针开放短路径

- 选定算法（首选）：**Held–Karp 动态规划求开放路**（Bellman / Held–Karp 1962）。起点 = 当前机器狗位置（不回到起点）；\(n\le 12\) 时 \(O(n^2 2^n)\) 可接受。自实现 bitmask DP，不引入 `python-tsp`。
- 选型理由：点数极少，精确解比 NN 更短；`v_jung_nn` 已证明在**完整 12 点**上换 NN 无效，但减点后的残余 4–8 点上精确序仍有价值。仅在 Q 选出的子集上运行，且仅当覆盖中途仍有插入（步骤 N）打乱顺序时重解。
- 候选：最便宜插入（RSL 1977，2-近似）——若实现 DP 有数值问题则回退。
- 参考资料：
  - Held, Karp. 1962；Bellman 1962；https://en.wikipedia.org/wiki/Held–Karp_algorithm
  - 开放 TSP 技巧：距离矩阵第一列置 0。https://github.com/fillipe-gsm/python-tsp（只作方法说明，不作为依赖）
- 接口约定：`coverage.open_path_order(start, pts) -> list[Point]`；空或 1 点原样返回。
- 依赖：标准库。

### 步骤 S：密采样覆盖证书

- 选定算法（首选）：与论文图 F1(d) 同一口径的**密网格前向可见性枚举**（Ma & Liu 定向扇区覆盖模型）：场点网格不低于 16 径向 × 180 角向，朝向 36（每 10°），判据仍为前瓣 ±90° 且距离 ≤ 1000 m。`directional_front_cover_ok` 增加 `dense: bool=False`；默认 False 保持 `v_nofar` 旧测试。pathopt 新点序不改点集，故密证书与 `v_nofar` 同点集——若密口径失败，只报告薄弱区，**不收缩点集**、不把 `v_nofar` 单测改为失败。
- 选型理由：现 6×48×24 跳过薄弱点；论文图已量到约 2.5% 负余量。Voronoi 旋转传感器部署（WSN 文献）不适用（机器狗不可旋转一个固定传感器阵）。
- 参考资料：
  - Ma, Liu. *On Coverage Problems of Directional Sensor Networks*. MSN 2005. https://doi.org/10.1007/11599463_70
  - `output/figures/QA_figures.md` F1(d) 采样表
- 接口约定：`directional_front_cover_ok(..., dense=False)`；`dense=True` 时用加密网格。
- 依赖：标准库。

### 步骤 T：mock-80 门禁

- 选定算法：现有 `q4_benchmark.py` 多种子混合源对照。先冻结 `run_q4()`（`v_nofar`）80 局的 mean VT / mean travel；再跑 `run_q4_pathopt()`。miss 必须为 0；mean travel 与 mean VT 均须下降。
- 参考资料：`src/q4_benchmark.py`；官方基线 `output/baselines.md`（仅演练阶段才比 8508.1 s）。
- 接口约定：`python q4_benchmark.py --profile v_nofar --seeds 80` 与 `--profile pathopt --seeds 80`。修复 `HuntPolicy` 不接受 `q4_outer_mode` 的现有断口（benchmark 传入该参数）。
- 依赖：标准库。

### 候选尝试记录（v1.3）

| 步骤 | 候选算法 | 状态 | 失败原因 |
|------|----------|------|----------|
| M | 问题 3 同口径路径段归因 | 采用 | |
| N | cheapest-insertion 增量绕行 | 采用（修订） | 默认 80 m 过严，几乎全部延后，定向定位 miss 上升；改为「本听点新听源必清」+ 400 m 增量插入 |
| N | 严格两阶段 \(\Delta=0\) | 失败 | 延后到覆盖结束再清，clear_miss 爆、有漏清 |
| N | TOPTW ILS | 未试 | 过重 |
| P | 极角 Morse 扇区锯齿 | 失败 | mock 漏清（seed=3 听后定位失败）；径向进出拉长主干 |
| P | 贪心 gain/dist 跳点 | 失败 | 跨场跳跃，行驶变差且漏清 |
| P | 阿基米德螺旋 | 未试 | |
| P | 12 辐条加密 | 未试 | |
| Q | Chvátal 加权贪心集合覆盖 | 未作为主路径 | 跳点版失败；减点仍由既有 `might_hear` / `_redundant_cover` 承担 |
| Q | 固定 12 点信息增益序 | **禁止** | 官方已否决 |
| R | Held–Karp 开放路 | 已实现备用 | 扇区巡游撤回后未接入默认 pathopt |
| S | 密网格前向枚举 | 采用 | `dense=True` 可选 |
| T | mock-24 对照 | 采用 | pathopt miss=0，均 VT 7561 vs 7769，均行驶 6179 vs 6393 |

| 任务 ID | 实现内容 | 关联步骤 | 参考资料 |
|---------|----------|----------|----------|
| T18 | 问题 4 `_move_decomposition` 填 planned/rejoin；单测加和 | M | Galceran 2013；现有 Q3 ledger 测 |
| T19 | pathopt 延后清除 + 增量插入阈值；解除定向「永不延后」的全局断言（改为只约束 v_nofar） | N | RSL 1977；现有 `_incremental_service_cost` |
| T20 | `sector_fused_order` + `_run_pathopt_cover`；`test_cover_inner_before_outer` 仅 v_nofar | P | Acar 2002 Morse |
| T21 | 贪心集合覆盖选下一听点；定向偏重 mock 外环访问数均值 < 12 且全清 | Q | Chvátal 1979；`might_hear` |
| T22 | `open_path_order` Held–Karp；在 pathopt 剩余点上调用 | R | Held–Karp 1962 |
| T23 | `directional_front_cover_ok(dense=...)` + 单测 | S | Ma & Liu 2005；QA_figures F1(d) |
| T24 | `run_q4_pathopt`；修好 benchmark 参数；mock 多种子对照 + 现有 `test_q4` 不回退 | T | `q4_benchmark.py` |

实现顺序：T18 → T19 → T20 → T21 / T22（可并行）→ T23 → T24。T24 之前 T18–T22 的单测与现有 `test_q4`（`run_q4`）必须通过。

## 变更 v1.4（交错搜索 + 开放最短路批量清除）

依据用户指令与 `01-architecture.md` v1.4。`run_q4()` 保持 `v_nofar`。

### 步骤 U：内外交错听点

- 选定算法：**极角 Morse 扇区锯齿**（`sector_fused_order`）。听点集仍为 `q4_listen_set`（原点 + 8×900 + 8×1200 + 12×2100）。偶数扇区半径升序，奇数扇区半径降序。原点先全扫。
- 选型理由：用户明确要求内外点交错，替代双环串行。v1.3 曾因漏清撤回锯齿；本变更用先搜后清 + 区域补清处理漏清，而不是改回双环。
- 接口：`HuntPolicy._run_stagger_search_cover`；覆盖期 pathopt 不 `_drain_pending`。
- 顺路第二看：`_q4_second_look_channels`（间距 80–1600 m、体坐标 `|y|≥200`、前瓣兼容）。**不用**带 `|P|≤1800` 裁剪的 `in_candidate_region`（否则 2100 m 外环点永远不合格）。

### 步骤 V：预测区域开放最短路清除

- 选定算法：对每个 pending 取预测点（两站且 `can_clear_20` 用包围圆心，否则 `recommend_second` 矩形代表点）→ `open_path_order`（Held–Karp n≤12，否则开放 NN+2-opt）从当前位置排序 → `_localize_and_clear` → 清一个再重解。
- 若交会区 >20 m：先在圆心周围 24/36/48 m 及 36 m 八方向扇形补清；失败再从第一听点做专用第二站（pathopt 优先 `recommend_second` 靠近源，而不是折返覆盖听点旁的 compact 点）。
- 接口：`HuntPolicy._batch_clear_by_path` / `_region_clear_point` / `_try_region_fan_clear`。

| 任务 ID | 实现内容 | 关联步骤 |
|---------|----------|----------|
| T25 | `_run_stagger_search_cover` + 覆盖期不 drain；交错单测 | U |
| T26 | `_batch_clear_by_path` + Held–Karp/2-opt；seed0 全清 | V |
| T27 | mock-24 对照；`run_q4()` 回归不回退 | U,V |

## 变更 v1.5（问题 3 滚动时域开放 TSP 清除）

依据用户指令：每移动一步，按机器狗当前位置与已知源估计点重解最短开放路。`run_q3()` 保持现行延后清除。

### 步骤 W：清除序动态重规划

- 选定算法（首选）：**滚动时域开放 TSP（RH-OTSP）**。
  1. 对每个 pending 信道，用当前位置重算估计服务点（单站 → `next_stations(now=·)`，两站 → 交会圆心）。
  2. `open_path_channel_order`：n≤12 Held–Karp 开放路，否则 NN+2-opt。
  3. 只执行第一条边的一个前缀（步长约 280 m，或到达则做一次定位/清除动作），然后用新位姿重解。
  4. 滞回 50 m：当前目标仍接近最优则不切换，避免左右摆。
  5. 若当前点已落入某源 20 m 或合法第二站，优先就地服务。
- 选型理由：场地无障碍，几何最短路就是折线访问序；n≤16 可每步精确/近精确重解。Ma & Castañón（CDC 2006）把 Dubins TSP 做成滚动三航点；Pavone 等 DTRP 的 sRH 策略是「求剩余点 TSP，走一段再重算」。本问题没有最小转弯半径，因此把 Dubins 段换成欧氏开放 HK。协议没有空驶，前缀必须落在 `/measure` 或 `/clear` 上，远距离第二站的中途检测顺便更新示向。
- 候选（按优先级，调试时依次）：
  1. RH-OTSP + 前缀截断（本版采用）
  2. 只在每次 `/measure`/`/clear` 后重解、不去截断（避免 5 s 中途检测）
  3. 纯最近邻滚动（无剩余路代价，易交叉）
  4. LKH / VNS 修补（n 太小，无必要依赖）
- 参考资料：
  - Ma, Castañón. *Receding Horizon Planning for Dubins Traveling Salesman Problems*. CDC 2006. https://doi.org/10.1109/cdc.2006.376928
  - Pavone, Frazzoli, Bullo. *Decentralized Algorithms for Stochastic and Dynamic Vehicle Routing*. CDC 2007. https://stanfordasl.github.io/wp-content/papercite-data/pdf/Pavone.Frazzoli.ea.CDC07.pdf
  - Psaraftis. *Dynamic vehicle routing problems*. Vehicle Routing: Methods and Studies, 1988.
  - Held, Karp. *A dynamic programming approach to sequencing problems*. J. SIAM 1962.
  - Gentilini, Sathiya, Pham. *RoboTSP*. arXiv:1709.09343. https://ar5iv.labs.arxiv.org/html/1709.09343
- 接口约定：`open_path_channel_order(start, {ch: xy}) -> [ch…]`；`HuntPolicy._rh_pick_channel` / `_rh_service_step`；统计 `q3_rh_replans` / `q3_rh_steps` / `q3_rh_switches`。
- 依赖：现有 `open_path_order`，无新库。

## 候选尝试记录

| 步骤 | 候选算法 | 状态 | 失败原因 |
|------|----------|------|----------|
| W | RH-OTSP + 前缀截断 | 采用 | — |
| W | 清完一个再 HK | 被本版替换 | 锁定整段 `_localize_and_clear`，中途不能换目标 |
| W | 纯最近邻 | 未试 | 作回退 |

## 任务分配

| 任务 ID | 实现内容 | 关联步骤 | 参考资料 |
|---------|----------|----------|----------|
| T28 | `open_path_channel_order` + RH 清除循环 + 单测截断/全清 | W | CDC 2006；Held–Karp |
| T29 | mock 多种子对照 `run_q3` vs `run_q3_batch`；更新 GIF | W | `fig_q3_path_gif.py` |
