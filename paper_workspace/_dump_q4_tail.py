from pathlib import Path
from docx import Document

DOC = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题4(1)-修订4.docx"
doc = Document(str(DOC))
lines = []
for i, para in enumerate(doc.paragraphs):
    t = para.text.strip()
    if i >= 105:
        lines.append(f"{i:04d} {t[:180]}")
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q4_tail.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)
