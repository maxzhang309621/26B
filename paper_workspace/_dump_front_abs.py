from pathlib import Path
from docx import Document

DOC = Path(
    r"c:\Users\max\xwechat_files\wxid_whiruqlnhzi712_2e9a\temp\RWTemp"
    r"\2026-09\805970c12c02fdc51e5af8cbfb1bb35a\2026B-前言-基础部分润色稿.docx"
)
doc = Document(str(DOC))
out = []
for i, para in enumerate(doc.paragraphs):
    if i > 7:
        break
    out.append(f"===== para {i} style={para.style.name} =====")
    out.append(repr(para.text))
    for j, run in enumerate(para.runs):
        out.append(f"  run{j}: {repr(run.text)}")
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_front_abs_runs.txt").write_text(
    "\n".join(out), encoding="utf-8"
)
