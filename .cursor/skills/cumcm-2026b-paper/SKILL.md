---
name: cumcm-2026b-paper
description: >-
  2026 高教社杯 B题（无线电干扰源定位与清除）论文写作：排版规范、四问结构、官方演练
  数字与 v_nofar 基线口径。Use when 写论文、续写、排版 docx、摘要、符号表、
  2026B、干扰源、覆盖航路、v_nofar、Q3 Q4 结果、高教社杯、cumcm-paper、数模论文.
---

# 2026B 论文写作 skill

本队 **2026 B 题**（无线电干扰源）论文接手包。通用排版继承 2025B cumcm-paper，**数字与策略口径以 2026B 为准**。

**先读** [handoff.md](handoff.md) → [results-and-decisions.md](results-and-decisions.md)。

## 文件导航

| 文件 | 何时读 |
|------|--------|
| [handoff.md](handoff.md) | **接手必读**：26B 路径、代码模块、四问章节 |
| [results-and-decisions.md](results-and-decisions.md) | 官方基线数字、v_nofar、消融对照 |
| [format-rules.md](format-rules.md) | Word 排版与文风硬规则 |
| [structure-template.md](structure-template.md) | 章节模板（本题为**四问**，增第八章） |
| [abstract-guide.md](abstract-guide.md) | 摘要骨架（四问各一段） |
| [writing-standards.md](writing-standards.md) | 文风补充 |
| [checklist.md](checklist.md) | 交稿质检 |

## 2026B 覆盖（优先于 2025B 习惯）

| 项 | 2026B 口径 |
|----|------------|
| 提交策略 Q4 | **`v_nofar`**：12×2100，`run_q4()`，8508 s / 10/10 |
| 提交策略 Q3 | **round3-q12**，5245 s / 10/10 |
| 题型 | 几何覆盖 + 序贯测向 + 清除（**非**干涉测厚） |
| 主证据 | `d:/index/数模/26B/output/q4-results/`、`output/drill/*batch*.json` |
| 插图 | `output/q4-results/fig1`–`fig8`、README 图例说明 |

2025B 专用（SiC 测厚、公式序号脚本、`B题论文-整体.docx`）**不要**套用到 2026B。

## 写作工作流

| 用户意图 | 做法 |
|----------|------|
| 写全文大纲 | [structure-template.md](structure-template.md) → 四问六段式 |
| 写摘要 | [abstract-guide.md](abstract-guide.md) + results 硬数字 |
| 写 Q3/Q4 策略 | handoff 代码表 + README 航路分层 |
| 写 Q1/Q2 几何 | `26B/docs/pipeline/02-algorithm-plan.md` |
| 排版/改 Word | [format-rules.md](format-rules.md) + [checklist.md](checklist.md) |
| 几何覆盖叙述 | 可选读 `工作区/先前工作/cumcm-method-playbook-portable/solving-playbooks.md` |

摘要建议硬数字：**Q3 5245 s、10/10**；**Q4 8508 s、10/10、677 s/源**；覆盖 **8×1200 + 12×2100**。

## 禁止

- 把 dynamic v2、outer11 消融当「提交策略」
- 混淆秒/停靠点与秒/干扰源
- 伪造演练数据；正式测试勿在 skill 流程中自动触发
- 抄 2025 年优秀论文正文
