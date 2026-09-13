# 问题 3 第 2–3 步代码与实验计划

## 已批准边界

- 人工决策：`q3_method_choice_20260911`、`q3_step1_result_proceed_steps2_3_20260911`。
- 主方法：`M2_triangulation_first`；基线为第 1 步 round1；`F1_bounded_creep` 仅在几何退化或再测量失败时兜底。
- 环境：Windows 原生 Python 3.12，仅标准库；固定种子 `0..99` 加 16 源边界场景。
- 禁止调用官方演练和正式测试；第 3 步验收后停在第 4 步之前。

## 第 2 步：保守物理可行域

1. 保留问题 1 的 `intersect_cones` 行为，新建 Q3 专用可行域函数。
2. 每个两位小数示向值采用 `1.01°` 保守半宽，覆盖 `±1°` 场地误差与最多 `0.005°` 输出舍入误差。
3. 将比赛圆域 `|G| <= 1800 m` 和每次正检测距离上界 `|G-S_i| <= 1500 m` 作为外接正多边形半平面，逐平面裁剪角锥交，得到真实可行域的保守外包络。
4. 仅当外包络最小包围圆半径不超过 `20 m` 时按圆心清除；这不会把不确定性低估。
5. `no_signal` 仅记录为排除圆 `|G-S_i| > 1000 m`。该约束非凸，不用于缩小清除证明；只用于候选测点排序和矛盾诊断。
6. 第二、第三测点均投影/筛选到半径 `1800 m` 的合法场地内；若候选失去再接收或几何价值，转入既有有界兜底。

## 第 3 步：顺路复测和增量代价调度

1. 主覆盖航路顺序不变，`run` 仍是唯一编排者，`_scan_point` 与 `_localize_and_clear` 不互相递归。
2. 一次覆盖扫描后，具有 1 次正方向观测的频道若能在后续覆盖航点形成合法第二站，则暂缓专程定位；到该航点时与未知频道一起复测。
3. 新增方向观测后立即尝试定位清除；路由末尾或没有合法后续复测点时，调用专程定位兜底。
4. 待处理频道按预计服务位置到当前位置的增量移动代价排序；并以较早发现次序稳定打破平局。
5. 记录顺路复测数、延后次数、专程定位次数和退出时 pending 数；不得改变 RobotClient 协议或 Q4 的 directional 分支。

## 验收与产物

- 硬门槛：round2、round3 固定 100 局均 `100/100` 全清，边界场景 `16/16`，全部单元测试通过，无非法协议动作。
- 次级比较：虚拟时间、动作数、测量数、方向数、清除数、creep 调用/步数；round3 另比较顺路复测与专程定位。
- 第 2 步：`results/Q3/experiments/round2/{metrics,run_summary.json}`。
- 第 3 步：`results/Q3/experiments/round3/{metrics,run_summary.json}`。
- 稳健性：`robustness/Q3/q3_robustness_summary.json`，覆盖角度 0/360、`±1.005°` 边界、场地/距离边界、无信号非凸约束和调度退化夹具。
- 审查：`code/Q3/reviews/q3_python_review.json` 必须完成 `syntax`、`input_contract`、`method_alignment`、`reproducibility`、`output_contract` 五项命名检查。

预计单轮 100 局本地 mock 为秒级；实现、回归和证据整理合计约 25–45 分钟。

## 第 4 步增补：解析覆盖证明与六环点候选

- 批准决策：`q3_steps2_3_result_proceed_step4_20260911`；比较基线为 round3 的 Q3 中心加 8 环点策略。
- 候选仅作用于 `directional=False`：先以中心点加半径 1200 m 的 6 个等角环点建立可行候选，再在固定的小范围参数筛选中将本轮评估候选定为半径 1150 m、相位 10°；Q4 继续使用原 8 个内环点和全部外环点。
- 解析证明：半径不超过 1000 m 的位置由中心覆盖；对 `r in [1000, 1800]`，最近环点夹角不超过 `pi/6`，距离平方为 `r^2 + 1150^2 - 2300*r*cos(pi/6)`。该凸二次式在区间上的最大值位于端点，最坏距离为 988.511 m，小于 1000 m。相位不影响覆盖证明，只影响固定样本上的访问顺序和代价。
- 实现应保留采样 `coverage_ok` 作为独立数值回归，并新增解析证书函数；不得仅凭随机样本宣布覆盖成立。
- round4 与 round3 使用相同种子 `0..99` 和同一 16 源边界场景。硬门槛：`100/100`、`16/16`、最大 pending=0、最大非法动作=0、退出全部 accepted；失败则 Q3 默认仍使用 8 环点。
- 次级指标：虚拟时间、动作数、测量数、方向数、顺路复测、专程补测定位；如只改善部分指标，必须明确报告权衡。
- 产物：`results/Q3/experiments/round4/metrics/candidate_metrics.json`、`results/Q3/experiments/round4/run_summary.json`，并刷新 Q3 稳健性摘要和 Python 审查。
- 第 4 步验收后停止，不进入第 5 步。

## Step 8 最小实现契约：clear-ready 跨未来主干边插入

- 授权依据：`q3_step7_accept_and_proceed_step8_20260911`；本单元只实现候选机制和小规模确定性验证，不进行 80 局、locked、官方演练或正式测试。
- active baseline：Step 7 原策略（当前 `src/policy.py` 的 `HuntPolicy(directional=False)`），行为对照必须保留；`src/q3_optimized_policy.py` 不属于当前入口，不修改。
- candidate 范围：仅处理 Q3 `directional=False` 且 `locate_quality(...)` 满足 `quality.can_clear_20`、`quality.sec_center` 合法并位于 Q3 场地内的 clear-ready 点 `C`。不改第二测站、全局 TSP、静态 `n/r/phase/CW-CCW` 或复杂权重。
- 插入规则：对尚未执行的主干边 `(A,B)` 计算 `delta = d(A,C) + d(C,B) - d(A,B)`，选择未来主干中的最小 `delta`；已执行边不可回滚，覆盖航点不可跳过，服务完成后必须回到该边的 `B` 端再继续主干。
- 调度状态：显式保存剩余主干边、已执行航点和已服务频道；同一频道不得重复 clear，未清频道不得从 pending 丢失；`directional=True` 不启用插入逻辑。
- 最小验证：单测覆盖插入代价公式/选边、不跳过覆盖航点、已清频道不重复，以及 directional 分支不采用插入；另做一个很小的确定性 smoke。不得以 smoke 结果宣称候选已采用或性能已改善。
- 产物门槛：若确有执行，最多生成 `results/Q3/experiments/step8_smoke/run_summary.json`，标明 candidate 未经 80/locked 验收且 active baseline 未切换；manifest 只可推进到 `implementation_ready_for_dev_eval`，不可标记 Step 8 完成。
- 后续验收：必须在独立 paired development/locked 集上证明 all-clear、协议与 P90 不退化后，才可考虑切换 baseline 或申请官方演练；本单元不进入 Step 9。
- 数据隔离：benchmark 必须显式使用 `--seed-start` 固定新 seed 区间；development 建议 `100..149`，locked 建议 `1000..1099`。先分别生成同区间 default-off baseline，再以 candidate 对该文件做 paired 比较，禁止拿历史 `0..79` 直接充当独立验证。

## Step 8 开发集验收结果

- 独立 development seeds `100..149` 已成对完成；基线与候选均 50/50 全清且协议指标正常。
- 候选相对基线均值慢 `53.5613 s`（`+1.0576%`），成对 P90 差 `+249.5687 s`，最坏回退 `+448.1996 s`，仅 24% case 更快。
- G8 的 mean 改善与尾部门槛失败，因此候选保持默认关闭，不运行 locked seeds `1000..1099`，不进入 Step 9。
- 当前 active baseline 仍是 Step 7 策略；后续若要冻结、官方演练或路线切换，均需单独授权。
