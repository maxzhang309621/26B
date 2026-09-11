# -*- coding: utf-8 -*-
"""LaTeX -> Word OMML equations (from cumcm-method-playbook portable)."""
from __future__ import annotations

import re
from copy import deepcopy
from lxml import etree
from latex2mathml.converter import convert as latex_to_mathml
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Pt, Cm
from docx.oxml.ns import qn

MML2OMML = r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"
_transform = None
_MATH_SPLIT = re.compile(r"\$(.+?)\$")
_CJK_LATIN = re.compile(r"([\u0000-\u007F]+)|([^\u0000-\u007F]+)")


def _sanitize_latex(latex: str) -> str:
    """latex2mathml 对 \\bigl/\\left 花括号常原样吐出反斜杠，Word 里会显示成 \\{。"""
    s = latex
    for cmd in (
        r"\biggl",
        r"\biggr",
        r"\Bigl",
        r"\Bigr",
        r"\bigl",
        r"\bigr",
        r"\left",
        r"\right",
    ):
        s = s.replace(cmd, "")
    s = s.replace(r"\mathrm{ang}", r"\angle")
    return s


def _get_transform():
    global _transform
    if _transform is None:
        _transform = etree.XSLT(etree.parse(MML2OMML))
    return _transform


def latex_to_omml(latex: str):
    mml = latex_to_mathml(_sanitize_latex(latex))
    tree = etree.fromstring(mml.encode("utf-8"))
    omml_tree = _get_transform()(tree)
    return omml_tree.getroot()


def _set_run_font(run, size=10.5, bold=False, *, latin="Times New Roman", east_asia="宋体"):
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = latin
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    for key in ("ascii", "hAnsi", "cs"):
        rFonts.set(qn(f"w:{key}"), latin)
    rFonts.set(qn("w:eastAsia"), east_asia)


def _append_text_runs(paragraph, text: str, *, size=10.5, bold=False, east_asia="宋体"):
    """中文、西文拆成不同 run，避免东亚逐字换行把英文标识从中间切断。"""
    if not text:
        return
    for ascii_part, cjk_part in _CJK_LATIN.findall(text):
        if ascii_part:
            run = paragraph.add_run(ascii_part)
            _set_run_font(run, size, bold, latin="Times New Roman", east_asia=east_asia)
            rPr = run._element.get_or_add_rPr()
            lang = rPr.find(qn("w:lang"))
            if lang is None:
                lang = OxmlElement("w:lang")
                rPr.append(lang)
            lang.set(qn("w:val"), "en-US")
            lang.set(qn("w:eastAsia"), "zh-CN")
        if cjk_part:
            run = paragraph.add_run(cjk_part)
            _set_run_font(run, size, bold, latin="Times New Roman", east_asia=east_asia)


def _set_no_midword_wrap(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    el = pPr.find(qn("w:wordWrap"))
    if el is None:
        el = OxmlElement("w:wordWrap")
        pPr.append(el)
    el.set(qn("w:val"), "0")


def _append_omath(paragraph, latex: str, display: bool = False):
    omath = latex_to_omml(latex)
    if omath.tag.endswith("oMathPara"):
        if display:
            paragraph._p.append(omath)
        else:
            for child in omath:
                if child.tag.endswith("oMath"):
                    paragraph._p.append(deepcopy(child))
                    return
            paragraph._p.append(omath)
        return
    if display:
        omath_para = OxmlElement("m:oMathPara")
        omath_para.append(deepcopy(omath))
        paragraph._p.append(omath_para)
    else:
        paragraph._p.append(deepcopy(omath))


def add_equation(doc, latex: str, numbered: str | None = None, *, font_size: float = 10.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.line_spacing = 1.0
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    _append_omath(p, latex, display=True)
    if numbered:
        run = p.add_run(f"    {numbered}")
        _set_run_font(run, font_size, False)
    return p


def add_mixed_paragraph(
    doc,
    text: str,
    *,
    first_indent: bool = True,
    center: bool = False,
    font_size: float = 10.5,
    line_spacing: float = 1.0,
    paragraph=None,
):
    p = paragraph or doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line_spacing
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if first_indent and not center:
        pf.first_line_indent = Cm(0.74)
    _set_no_midword_wrap(p)
    pos = 0
    for m in _MATH_SPLIT.finditer(text):
        if m.start() > pos:
            _append_text_runs(p, text[pos : m.start()], size=font_size)
        _append_omath(p, m.group(1), display=False)
        pos = m.end()
    if pos < len(text):
        _append_text_runs(p, text[pos:], size=font_size)
    return p
