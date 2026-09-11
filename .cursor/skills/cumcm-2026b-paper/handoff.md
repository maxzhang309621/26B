# 2026B 论文接手（无线电干扰源）

## 项目根目录

`d:/index/数模/26B`

队号：`202610057095`（`robot_id.txt` 本地填写，勿提交）

## 先读什么

1. [results-and-decisions.md](results-and-decisions.md) — 官方数字、基线、秒/源
2. `26B/output/q4-results/README.md` — Q4 航路分层与图说明
3. `26B/output/q4-results/OFFICIAL_PRACTICE_SUMMARY.md` — 全部官方演练批次
4. `26B/docs/pipeline/01-architecture.md` — 四问目标与模块
5. `26B/docs/pipeline/02-algorithm-plan.md` — 算法选型与文献

## 代码与策略（写问题 3/4 必引）

| 模块 | 路径 | 论文对应 |
|------|------|----------|
| 几何核 Q1 | `src/geometry.py` | 半平面交、直径、Welzl 圆 |
| 候选区 Q2 | `src/candidate.py` | 第二站、正交配置 |
| 覆盖 Q3/Q4 | `src/coverage.py` | 8×1200、900 途听、12×2100 |
| 策略 | `src/policy.py` `HuntPolicy` | 序贯搜索 + 定位清除 |
| Q3 入口 | `src/runner_q3.py` | 全向 round3 |
| **Q4 提交** | `src/runner_q4.py` **`run_q4()`** | **v_nofar 基线** |
| Q4 实验 | `src/runner_q4.py` `run_q4_v2()` | 动态外环（勿当提交版） |

**提交/正式测试默认：`v_nofar`**（12×2100 固定外环，`dynamic_pure`）。

## 已有插图（PNG，本地 gitignore 未跟踪时需现场生成）

`output/q4-results/`：`fig1`–`fig8`、`v_nofar_cover_path.png`  
生成脚本：`src/plot_q4_practice_games.py`、`src/viz.py`、`src/q1_cli.py`

## 论文章节建议（四问）

| 章 | 内容 |
|----|------|
| 五 | 问题一：角扇半平面交、定位区直径、直径圆覆盖（荣格/Jung） |
| 六 | 问题二：第二检测点、候选区、GDOP/正交 |
| 七 | 问题三：圆覆盖航路、频道调度、官方 **5245 s / 10/10** |
| 八 | 问题四：定向 180° 前瓣、外环覆盖、**v_nofar 8508 s / 10/10** |

每问六段式见 [structure-template.md](structure-template.md)（模板为三问，本题为四问，增「问题四」一章）。

## 题型 playbook（几何覆盖）

通用步骤见：`d:/index/数模/工作区/先前工作/cumcm-method-playbook-portable/solving-playbooks.md`  
题型：**几何覆盖 / 序贯决策**（非 2025B 光学测厚）。

## 禁止

- 把 dynamic v2（9371 s）写成提交策略；正式口径 **v_nofar 8508 s**
- 把「秒/停靠点」与「秒/干扰源」混用（整局约 **677 s/源**）
- 伪造官方演练数字；以 `output/drill/`、`output/q4-results/` JSON 为准
- 自动触发正式测试（各 3 次）
