from pathlib import Path
from lxml import etree
from docx import Document
from docx.oxml.ns import qn

DOC = Path(
    r"c:\Users\max\xwechat_files\wxid_whiruqlnhzi712_2e9a\temp\RWTemp"
    r"\2026-09\805970c12c02fdc51e5af8cbfb1bb35a\2026B-前言-基础部分润色稿.docx"
)
doc = Document(str(DOC))
para = doc.paragraphs[4]
xml = para._p.xml
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_front_p4.xml").write_text(xml, encoding="utf-8")
print("len", len(xml), "omath", xml.count("oMath"))
