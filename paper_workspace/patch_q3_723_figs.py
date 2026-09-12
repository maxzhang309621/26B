"""Insert 7.2.3 evolution figures and renumber later figures 6–10 → 8–12."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from shutil import copy2

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph

DOC = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题3(2)-修订3.docx"
OUT = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题3(2)-修订4.docx"
WX = Path(
    r"c:\Users\max\xwechat_files\wxid_whiruqlnhzi712_2e9a\temp\RWTemp"
    r"\2026-09\805970c12c02fdc51e5af8cbfb1bb35a\2026B-问题3(2).docx"
)
ALT = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题3(2)-修订.docx"
FIG_COST = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q3_scan_clear_cost.png")
FIG_TAIL = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q3_scan_clear_tail.png")
DUMP = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q3_723_after.txt")

REMAP = (
    ("图 10", "图 12"),
    ("图 9", "图 11"),
    ("图 8", "图 10"),
    ("图 7", "图 9"),
    ("图 6", "图 8"),
)
SPLIT_NUM = {"10": "12", "9": "11", "8": "10", "7": "9", "6": "8"}


def remap_run_list(runs) -> None:
    for i, run in enumerate(runs):
        t = run.text
        if not t:
            continue
        for old, new in REMAP:
            t = t.replace(old, new)
        stripped = t.strip()
        if stripped in SPLIT_NUM and i > 0:
            prev = runs[i - 1].text or ""
            if prev.rstrip().endswith("图"):
                t = t.replace(stripped, SPLIT_NUM[stripped], 1)
        run.text = t


def remap_document(doc: Document) -> None:
    for para in doc.paragraphs:
        remap_run_list(para.runs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    remap_run_list(para.runs)


def blank_after(anchor, style_para: Paragraph) -> Paragraph:
    new_elm = deepcopy(style_para._p)
    p_pr = new_elm.find(qn("w:pPr"))
    for child in list(new_elm):
        if child is not p_pr:
            new_elm.remove(child)
    if hasattr(anchor, "_p"):
        anchor._p.addnext(new_elm)
    else:
        anchor.addnext(new_elm)
    return Paragraph(new_elm, style_para._parent)


def add_figure_block(anchor, style_para: Paragraph, png: Path, caption: str, note: str, width_cm: float):
    """Insert pointer/image/caption/note immediately after anchor, in that order."""
    note_p = blank_after(anchor, style_para)
    cap_p = blank_after(anchor, style_para)
    img_p = blank_after(anchor, style_para)
    img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = img_p.add_run()
    run.add_picture(str(png), width=Cm(width_cm))
    cap_p.add_run(caption)
    note_p.add_run(note)
    return img_p, cap_p, note_p


def main() -> None:
    doc = Document(str(DOC))
    remap_document(doc)

    p48 = p49 = p52 = cap_style = None
    for para in doc.paragraphs:
        t = para.text.strip()
        if t.startswith("针对干扰源位置未知且移动代价"):
            p48 = para
        if t.startswith("三类代表性探索足以说明"):
            p49 = para
        if t.startswith("据此，本文不把边扫边清"):
            p52 = para
        if t.startswith("图 5") or t.startswith("图 5  "):
            cap_style = para
    if cap_style is None:
        for para in doc.paragraphs:
            if para.text.startswith("图 2  "):
                cap_style = para
                break
    if not all([p48, p49, p52, cap_style]):
        raise RuntimeError(f"missing anchors {p48, p49, p52, cap_style}")

    # pointer on last run of p48 (after OMML)
    if p48.runs:
        p48.runs[-1].text = (p48.runs[-1].text or "").rstrip("。") + "。时间账本与阶段性压缩见图 6。"
    if p49.runs:
        p49.runs[-1].text = (p49.runs[-1].text or "").rstrip("。") + "。均值改善与配对尾部回退见图 7。"

    add_figure_block(
        p48,
        cap_style,
        FIG_COST,
        "图 6  边扫边清在线路线的时间压缩与账本构成（本地 Mock，非正式测试）",
        "左图由局部试探转向交会优先、再至增量调度，均时下降但并未消除后续路径耦合。"
        "右图为后续严格基线：移动约占 85.9%，其中清除绕行约占 36.6%，说明主要剩余矛盾是服务动作把机体带离覆盖主干。",
        16.2,
    )

    tbl = doc.tables[1]._tbl
    add_figure_block(
        tbl,
        cap_style,
        FIG_TAIL,
        "图 7  边扫边清代表性候选的均值改善与配对 P90 回退（本地 Mock，非正式测试）",
        "横轴正值表示相对成对基线变快。右上象限均值改善但尾部回退，故未进入主线；"
        "六点环在在线清除逻辑下均值与尾部均劣于八点基准，说明短主干并不能在边扫边清中自动兑现。"
        "跨未来边插入均值变慢约 1.1%，仅见表 3，不进入本图。",
        14.6,
    )

    p52.runs[0].text = (
        "在线小批次服务与第二测站交会角审计因同时就绪目标过少、低交会角比例不足，未形成独立入口。"
        "据此，本文不把边扫边清表述为失败的尝试，而表述为必要的结构性探索："
        "它揭示了在线耦合下“均值改善不等于尾部稳定”，并筛选出可迁移至先搜后清骨架的环边补测与有限顺路清除；"
        "最终主模型由覆盖完备性判据、开放服务路径与滚动重规划共同支撑，证据链更易分层审计。"
    )

    doc.save(str(OUT))
    copies = {}
    for dest, key in ((WX, "wechat"), (ALT, "修订"), (DOC, "修订3")):
        try:
            copy2(OUT, dest)
            copies[key] = True
        except OSError:
            copies[key] = False

    d2 = Document(str(OUT))
    lines = [f"paras={len(d2.paragraphs)} tables={len(d2.tables)} copies={copies}"]
    for i, para in enumerate(d2.paragraphs):
        t = para.text.strip()
        if any(k in t for k in ("7.2.3", "图 6", "图 7", "图 8", "图 9", "图 10", "图 11", "图 12", "边扫边清", "据此，本文")):
            lines.append(f"{i:04d} {t[:200]}")
    DUMP.write_text("\n".join(lines), encoding="utf-8")
    print("saved", OUT)
    print("copies", copies)


if __name__ == "__main__":
    main()
