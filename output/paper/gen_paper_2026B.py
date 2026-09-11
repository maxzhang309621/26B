# -*- coding: utf-8 -*-
"""Generate 2026 B题 Word paper from team results (v_nofar baseline)."""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
FIG = ROOT / "output" / "q4-results"
OUT = Path(__file__).resolve().parent / "2026B论文.docx"

sys.path.insert(0, str(SRC))
from word_math import add_equation, add_mixed_paragraph  # noqa: E402


def set_run_font(run, name="宋体", size=12, bold=False, east="宋体"):
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), east)


def H(doc, text, level=1):
    p = doc.add_paragraph()
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        set_run_font(run, "黑体", 16, True, "黑体")
    elif level == 1:
        run = p.add_run(text)
        set_run_font(run, "黑体", 14, True, "黑体")
    else:
        run = p.add_run(text)
        set_run_font(run, "黑体", 12, True, "黑体")
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)


def P(doc, text, first_indent=True):
    if "$" in text:
        return add_mixed_paragraph(doc, text, first_indent=first_indent)
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if first_indent:
        pf.first_line_indent = Cm(0.74)
    run = p.add_run(text)
    set_run_font(run, "宋体", 12, False, "宋体")


def Eq(doc, latex, num=None):
    add_equation(doc, latex, numbered=num)


def Cap(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, "宋体", 10.5, False, "宋体")
    p.paragraph_format.space_after = Pt(8)


def Img(doc, path, width=5.2, caption=None):
    path = Path(path)
    if not path.is_file():
        P(doc, f"[缺图: {path.name}]", first_indent=False)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    if caption:
        Cap(doc, caption)


def Tab(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(h))
        set_run_font(run, "宋体", 9, True, "宋体")
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(val))
            set_run_font(run, "Times New Roman", 9, False, "宋体")
    doc.add_paragraph()


def build():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(2.54)
        sec.bottom_margin = Cm(2.54)
        sec.left_margin = Cm(2.5)
        sec.right_margin = Cm(2.5)

    H(doc, "基于角扇交会与分层覆盖的无线电干扰源快速定位清除模型", 0)

    H(doc, "摘  要", 1)
    P(
        doc,
        "无线电干扰源的快速发现、精确定位与清除，是电子对抗与频谱管控中的典型序贯决策问题。"
        "本文面向 2026 高教社杯 B 题，在半径 1800 m 的圆形任务区内，建立由计算几何、覆盖路径与序贯测向串联的统一框架，"
        "并给出可对接官方模拟器的机器狗控制策略。",
    )
    P(
        doc,
        "针对问题一，将示向度误差 ±1° 转化为 2° 闭角扇，以半平面交得到定位区 $R$，计算直径 $d$ 与 Welzl 最小包围圆半径 $r$，"
        "并判定直径圆能否覆盖 20 m 光学清除区。",
    )
    P(
        doc,
        "针对问题二，以两站交会角接近 90° 时的 GDOP 最优性为依据，构造第二检测点的正交侧向推荐规则与候选区域；"
        "对定向干扰源增加前瓣可见性约束。",
    )
    P(
        doc,
        "针对问题三，采用原点 + 8×1200 m 等圆覆盖航路，配合顺路复测与延后专程定位清除；"
        "官方问题 3 演练 10 局 10/10 全清，平均虚拟时间 5245 s（约 475 s·源$^{-1}$）。",
    )
    P(
        doc,
        "针对问题四，增加射线上 900 m 途听与 12×2100 m 外环；提交策略 v_nofar 在官方问题 4 演练 10 局 10/10 全清，"
        "平均虚拟时间 8508 s（约 677 s·源$^{-1}$）；时间瓶颈主要来自外环空驶（约占 84%）。",
    )
    P(doc, "关键词：半平面交会；圆覆盖；序贯测向；分层航路；虚拟时间优化", first_indent=False)

    H(doc, "一、问题重述", 1)
    H(doc, "1.1 问题背景", 2)
    P(
        doc,
        "机器狗在半径 1800 m 的圆形任务区内搜索 1–20 频道干扰源，通过 /measure 获取示向度，"
        "通过 /clear 在 20 m 内清除。速度 5 m/s，单次检测 5 s，换频 1 s；"
        "每源有效接收半径 $r_{\\mathrm{eff}}\\in[1000,1500]$ m。",
    )
    H(doc, "1.2 问题要求", 2)
    P(doc, "问题一：多站示向度交会定位区与可清除性。问题二：第二检测点策略与候选区。")
    P(doc, "问题三：全向源自动搜索清除。问题四：含定向源的搜索清除。")

    H(doc, "二、问题分析", 1)
    P(doc, "四问构成递进链路：问题一给出清除几何边界；问题二决定补测点；问题三决定听点覆盖；问题四扩展定向前瓣与外环。")
    Tab(
        doc,
        ["问题", "核心难点", "主方法"],
        [
            ["一", "示向度误差、半平面交", "计算几何"],
            ["二", "交会角退化、定向前瓣", "AOA 正交配置"],
            ["三", "未知源数、频道调度", "圆覆盖 + 序贯插入"],
            ["四", "定向后瓣、外场朝外源", "分层航路"],
        ],
    )

    H(doc, "三、符号说明", 1)
    Tab(
        doc,
        ["符号", "含义", "单位"],
        [
            ["Si", "第 i 次检测站坐标", "m"],
            ["θi", "示向度（正东 0°）", "°"],
            ["R", "定位区", "—"],
            ["d", "diam(R)", "m"],
            ["reff", "有效接收半径", "m"],
            ["VT", "虚拟时间", "s"],
        ],
    )

    H(doc, "四、模型假设", 1)
    for i, s in enumerate(
        [
            "示向度误差 ±1°，同点重复测量误差不变。",
            "单站用两个半平面表示 2° 闭角扇，不含对顶小扇。",
            "每频道至多一个源；问题三、四每局源数 N∈[10,16]。",
            "全向源：检测点在 reff 圆盘内可听；定向源：还须在前瓣 ±90° 内。",
            "清除仅看距离 ≤20 m；策略覆盖按 reff=1000 m 最坏设计。",
        ],
        1,
    ):
        P(doc, f"{i}. {s}")

    H(doc, "五、问题一：示向度交会定位区与可清除性", 1)
    H(doc, "5.1 角扇半平面", 2)
    P(doc, "在检测点 S 处示向度 θ 对应误差区间 [θ−1°, θ+1°]，转化为两条有向边界围成的闭角扇，不含对顶 2° 小扇。")
    H(doc, "5.2 多站定位区", 2)
    Eq(doc, r"R = \bigcap_{i=1}^{n} \mathcal{H}^+(S_i,\theta_i)", "(1)")
    P(doc, "对 n 条半平面两两求交，过滤满足全部约束的顶点并按极角排序得凸多边形。")
    H(doc, "5.3 直径与最小包围圆", 2)
    Eq(doc, r"d = \max_{p,q\in R}\|p-q\|", "(2)")
    P(doc, "采用 Welzl 算法求最小包围圆 (c,r)；若 r≤20 m 则以 c 为清除点。")
    H(doc, "5.4 Jung 定理", 2)
    Eq(doc, r"r \le \frac{d}{\sqrt{3}}", "(3)")
    P(doc, "直径圆半径 d/2 为保守上界，与 r 一并报告供策略选用。")

    H(doc, "六、问题二：第二检测点策略与候选区", 1)
    P(doc, "两站 AOA 交会角 β 接近 90° 时 GDOP 最优。名义源 Ĝ=S1+ρ·u(θ)，ρ=450 m；两侧法向偏移 H=400 m 得紧凑正交站。")
    P(doc, "定向源第二站须满足 front_compatible，落在第一次可听半平面内。候选区与 1800 m 任务圆、可听盘求交。")

    H(doc, "七、问题三：全向干扰源搜索清除策略", 1)
    H(doc, "7.1 覆盖航路", 2)
    P(doc, "取原点 + 8 点环，环半径 1200 m、等角 45°，边界采样验证任 |P|=1800 m 点到最近航路点 ≤1000 m。")
    H(doc, "7.2 频道与 round3", 2)
    P(doc, "原点 1→20 全扫；之后只扫未知信道。内环 NN 巡游 + 顺路复测 + 延后专程 drain。")
    H(doc, "7.3 官方演练结果", 2)
    Tab(
        doc,
        ["指标", "数值"],
        [
            ["全清率", "10/10"],
            ["平均 VT", "5245 s"],
            ["VT/源", "475 s·源⁻¹"],
            ["最短/最长", "4612 s / 6258 s"],
        ],
    )

    H(doc, "八、问题四：全向与定向干扰源搜索清除", 1)
    H(doc, "8.1 分层航路 v_nofar（提交策略）", 2)
    P(
        doc,
        "原点 20 信道全扫 → 去内环射线上 900 m 途听 → 8×1200 m 内环 → 12×2100 m 外环 → pending 扫尾。"
        "内圈不压制外圈；内环完成后 assume_directional 剪枝。",
    )
    Img(doc, FIG / "fig1_cover_layers.png", 5.0, "图1  航路分层示意")
    Img(doc, FIG / "fig3_directional_outward.png", 5.0, "图2  近心朝外定向源与听点")
    Img(doc, FIG / "fig5_walk_cover_only.png", 5.0, "图3  v_nofar 覆盖行走路径")
    H(doc, "8.2 定位清除", 2)
    P(doc, "紧凑正交第二站（H=400, ρ=450）；Q4 跳过远第二站；creep≤8 步；扇形 12 m+18 m 清除。")
    H(doc, "8.3 时间结构", 2)
    P(doc, "10 局均值：行驶 7169 s（84.3%），探测 1246 s（14.7%）；平均 677 s·源⁻¹。")
    H(doc, "8.4 官方演练明细", 2)
    Tab(
        doc,
        ["局", "源数", "全向+定向", "清除", "VT(s)"],
        [
            ["1", "12", "11+1", "12/12", "8465"],
            ["2", "13", "11+2", "13/13", "8042"],
            ["3", "16", "0+16", "16/16", "7710"],
            ["4", "11", "6+5", "11/11", "9115"],
            ["5", "16", "12+4", "16/16", "6162"],
            ["6", "10", "0+10", "10/10", "8534"],
            ["7", "14", "9+5", "14/14", "8463"],
            ["8", "15", "9+6", "15/15", "9370"],
            ["9", "12", "2+10", "12/12", "10283"],
            ["10", "11", "1+10", "11/11", "8937"],
        ],
    )
    P(doc, "合计 10/10 全清，均时 8508 s。")

    H(doc, "九、模型评价与结论", 1)
    P(doc, "优点：统一几何核、可证覆盖、演练稳定（Q3 5245 s、Q4 8508 s，均 10/10 全清）。")
    P(doc, "不足：未达 VT≤5000 s 目标；外环 2100 m 空驶占比高。外环 11×1900 虽 VT 8421 s 更低但 9/10 全清，不作提交版。")
    P(
        doc,
        "结论：覆盖路径长度而非单次检测驻留主导虚拟时间；定向前瓣使外环成为必要时间成本。"
        "提交策略 v_nofar 为官方演练最优全清方案。",
    )

    H(doc, "参考文献", 1)
    refs = [
        "[1] Shamos M I, Hoey D. Geometric intersection problems[C]//FOCS, 1976.",
        "[2] Welzl E. Smallest enclosing disks (balls and ellipsoids)[C]//LNCS 555, 1991.",
        "[3] Jung H. Über die kleinste Kugel[J]. J. reine angew. Math., 1901.",
        "[4] Doğançay K, Hmam H. Optimal angular sensor separation[J]. Signal Processing, 2008.",
        "[5] Galceran E, Carreras M. A survey on coverage path planning[J]. RAS, 2013.",
        "[6] 2026 高教社杯 B 题赛题及附件 1、2.",
    ]
    for r in refs:
        P(doc, r, first_indent=False)

    doc.save(OUT)
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
