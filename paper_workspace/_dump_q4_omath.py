from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

DOC = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题4(1)-修订4.docx"
doc = Document(str(DOC))
lines = []
for i, para in enumerate(doc.paragraphs):
    if not (19 <= i <= 45 or 104 <= i <= 112):
        continue
    n_om = para._p.xml.count("oMath")
    n_t = len(para.runs)
    t = para.text[:200].replace("\n", " ")
    lines.append(f"{i:04d} omath={n_om} runs={n_t} {t}")
out = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q4_omath.txt")
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
