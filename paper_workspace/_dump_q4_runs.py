from pathlib import Path
from docx import Document

DOC = Path(r"D:\maxzhang\python files\Math-modeling\26B\paper_workspace") / "2026B-问题4(1)-修订4.docx"
doc = Document(str(DOC))
out = []
for i, para in enumerate(doc.paragraphs):
    if i not in (20, 21, 31, 33, 34, 35, 37, 39, 40, 106, 107, 108):
        continue
    out.append(f"===== para {i} =====")
    out.append(repr(para.text[:240]))
    for j, run in enumerate(para.runs):
        out.append(f"  run{j}: {repr(run.text)}")
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q4_runs.txt").write_text(
    "\n".join(out), encoding="utf-8"
)
