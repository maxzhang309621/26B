"""Rewrite Q3(2) 7.2.1: hexagon time-optimal proof + hexagon figure + local coverage certificate."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
from shutil import copy2
import zipfile

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from PIL import Image

SRC = Path(
    r"c:\Users\max\xwechat_files\wxid_whiruqlnhzi712_2e9a\temp\RWTemp"
    r"\2026-09\805970c12c02fdc51e5af8cbfb1bb35a\2026B-问题3(2).docx"
)
OUT = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace\2026B-问题3(2)-修订.docx")
MEDIA = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q3v2_media")
FIG = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q3_hexagon_cover_pair.png")
EXTRACT = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q3v2_after.txt")

TIME_PROOF = (
    "覆盖巡游的虚拟时间须把几何路程与协议动作一并计入。"
    "原点对 1–20 信道全扫耗时 119 s；每个环点在最坏情形下仍须扫描全部未知信道，单点驻留 120 s。"
    "先搜后清的开放巡游路程为 ρ+(n−1)·2ρ sin(π/n)，以 5 m/s 折合行驶时间，故"
    "T(n,ρ)=[ρ+(n−1)·2ρ sin(π/n)]/5 + 119 + 120n。"
    "覆盖刚成立的最小半径下：五点环越界；六、七、八边形巡游总时分别约 2187 s、2197 s、2272 s。"
    "多一个顶点虽能缩短环向行驶，但每个环点多付一轮检测与换频，总时上升，故正六边形是耗时最短的可行方案。"
    "本文取 ρ=1150 m，略高于六边形门槛 1123 m，最坏距离约 988.5 m，巡游总时约 2219 s，仍低于七、八边形的最小半径方案。"
)


def rewrite_plain(para, text: str) -> None:
    if para.runs:
        para.runs[0].text = text
        for run in para.runs[1:]:
            run.text = ""
    else:
        para.add_run(text)


def insert_after(after_para, text: str, style_para=None) -> Paragraph:
    src = style_para or after_para
    new_elm = deepcopy(src._p)
    p_pr = new_elm.find(qn("w:pPr"))
    for child in list(new_elm):
        if child is not p_pr:
            new_elm.remove(child)
    after_para._p.addnext(new_elm)
    new_para = Paragraph(new_elm, after_para._parent)
    run = new_para.add_run(text)
    if src.runs:
        r_pr = src.runs[0]._r.find(qn("w:rPr"))
        if r_pr is not None:
            run._r.insert(0, deepcopy(r_pr))
    return new_para


def set_cell(cell, text: str) -> None:
    paras = cell.paragraphs
    if not paras:
        return
    if paras[0].runs:
        paras[0].runs[0].text = text
        for run in paras[0].runs[1:]:
            run.text = ""
    else:
        paras[0].add_run(text)
    for para in paras[1:]:
        for run in para.runs:
            run.text = ""


def compose_figure() -> tuple[int, int]:
    left = Image.open(MEDIA / "image2.png").convert("RGBA")
    cert = Image.open(MEDIA / "image8.png").convert("RGBA")
    w, h = left.size
    crop_w = int(round(w * 0.50))
    hex_panel = left.crop((0, 0, crop_w, h))
    scale = h / cert.height
    cert = cert.resize((max(1, int(round(cert.width * scale))), h), Image.Resampling.LANCZOS)
    gap = 16
    canvas = Image.new("RGBA", (hex_panel.width + gap + cert.width, h), (255, 255, 255, 255))
    canvas.paste(hex_panel, (0, 0))
    canvas.paste(cert, (hex_panel.width + gap, 0), cert)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIG)
    return canvas.size


def replace_media(docx_path: Path, png_path: Path, old_cx: int, old_cy: int) -> None:
    w_px, h_px = Image.open(png_path).size
    new_cy = int(round(old_cx * h_px / w_px))
    tmp = docx_path.with_suffix(".tmp.docx")
    old_extent = f'cx="{old_cx}" cy="{old_cy}"'
    new_extent = f'cx="{old_cx}" cy="{new_cy}"'
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/media/image2.png":
                data = png_path.read_bytes()
            elif item.filename == "word/document.xml":
                xml = data.decode("utf-8")
                xml = xml.replace(old_extent, new_extent, 2)
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(docx_path)


def extract_text(doc: Document, path: Path) -> None:
    lines = [f"paragraphs={len(doc.paragraphs)} tables={len(doc.tables)}"]
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            lines.append(f"{i:04d} {text}")
    lines.append("")
    lines.append("===== TABLES =====")
    for ti, table in enumerate(doc.tables):
        lines.append(f"--- table {ti} {len(table.rows)}x{len(table.columns)} ---")
        for ri, row in enumerate(table.rows):
            cells = " | ".join(c.text.replace("\n", " ") for c in row.cells)
            lines.append(f"  r{ri}: {cells}")
    path.write_text("\n".join(lines), encoding="utf-8")


def fig2_extent(docx_path: Path) -> tuple[int, int]:
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    key = 'name="Picture 2"'
    i = xml.find(key)
    window = xml[max(0, i - 250) : i + 80]
    cx = int(window.split('cx="')[1].split('"')[0])
    cy = int(window.split('cy="')[1].split('"')[0])
    return cx, cy


def main() -> None:
    copy2(SRC, OUT)
    compose_figure()
    cx, cy = fig2_extent(OUT)

    doc = Document(str(OUT))
    p = doc.paragraphs

    p[16].runs[1].text = "正六边形检测点：覆盖几何与动作时间最优性"

    p[22].runs[12].text = (
        "，不随源的空间分布自适应调整。"
        "图 2 左仅给出本文正六边形检测点，右图附本地已有覆盖证书；表"
    )
    p[22].runs[14].text = "按几何覆盖与动作驻留合计给出耗时对照，不再并列八边形分布图。"
    p[22].runs[16].text = ""

    insert_after(p[22], TIME_PROOF, style_para=p[20])

    rewrite_plain(p[23], "表 2  覆盖约束下正 n 边形覆盖巡游耗时对照（最不利接收半径 1000 m）")
    rewrite_plain(p[26], "图 2  正六边形检测点几何分布（左）与覆盖证书（右）")
    rewrite_plain(
        p[27],
        "左图为本文采用的原点加正六边形 6×1150 m（相位 10°）检测点；浅盘为半径 1000 m 可听范围。"
        "右图为本地覆盖证书：最不利边界点到最近环点 988.5 m，余量约 11.5 m，证书通过。"
        "不再并列八边形分布图；八点方案仅作为表 2 中的耗时对照。",
    )

    table = doc.tables[1]
    headers = ["方案", "覆盖", "环半径/m", "驻留动作/s", "巡游总时/s"]
    rows = [
        ["五点环", "否", "—", "—", "—"],
        ["正六边形（最小半径）", "是", "1123", "839", "2187"],
        ["正七边形（最小半径）", "是", "997", "959", "2197"],
    ]
    extra_rows = [
        ["正八边形（最小半径）", "是", "938", "1079", "2272"],
        ["正六边形（本文）", "是", "1150", "839", "2219"],
    ]
    for j, h in enumerate(headers):
        set_cell(table.rows[0].cells[j], h)
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            set_cell(table.rows[i].cells[j], val)
    for vals in extra_rows:
        new_row = table.add_row()
        for j, val in enumerate(vals):
            set_cell(new_row.cells[j], val)

    doc.save(str(OUT))
    replace_media(OUT, FIG, cx, cy)
    extract_text(Document(str(OUT)), EXTRACT)
    try:
        copy2(OUT, SRC)
        copied = True
    except OSError:
        copied = False
    print("saved", OUT)
    print("copied_src", copied)
    print("fig", Image.open(FIG).size, "old_extent", cx, cy)


if __name__ == "__main__":
    main()
