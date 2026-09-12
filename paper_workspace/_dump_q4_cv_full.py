from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

DOC = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题4(1)-修订5.docx"
doc = Document(str(DOC))
lines = []
for i, para in enumerate(doc.paragraphs):
    if not (19 <= i <= 40 or 96 <= i <= 115):
        continue
    n_om = para._p.xml.count("oMath")
    n_img = len(para._p.findall(".//" + qn("w:drawing")))
    t = para.text.strip().replace("\n", " ")
    extra = f" img={n_img}" if n_img else ""
    lines.append(f"{i:04d} om={n_om}{extra} {t[:190]}")
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q4_cv_full.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)
