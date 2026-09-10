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
