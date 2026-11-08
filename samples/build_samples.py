"""Build the sample corpus (DOCX / PDF / DOC / TXT) from the plain sources in samples/src.

    python samples/build_samples.py

PDF and DOC conversion use LibreOffice in headless mode (``soffice``).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.shared import Pt

HERE = Path(__file__).parent
SRC = HERE / "src"
ARABIC_HEADING = re.compile(r"^(ال)?(فصل|باب)\b")


def _rtl(paragraph) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    bidi = ppr.makeelement(qn("w:bidi"), {})
    ppr.append(bidi)
    for run in paragraph.runs:
        rpr = run._r.get_or_add_rPr()
        rpr.append(rpr.makeelement(qn("w:rtl"), {}))
        run.font.name = "FreeSerif"
        run.font.size = Pt(13)


def text_to_docx(src: Path, dst: Path, rtl: bool = False, title_first_line: bool = True) -> None:
    d = docx.Document()
    lines = [l.rstrip() for l in src.read_text(encoding="utf-8").splitlines()]
    first = True
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("## ") or (rtl and ARABIC_HEADING.match(line)):
            p = d.add_heading(line.lstrip("# ").strip(), level=2)
        elif line.startswith("# ") or (first and title_first_line):
            p = d.add_heading(line.lstrip("# ").strip(), level=1)
        else:
            p = d.add_paragraph(line)
        first = False
        if rtl:
            _rtl(p)
    d.core_properties.title = lines[0].lstrip("# ")
    d.save(dst)


def convert(src: Path, fmt: str) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("LibreOffice (soffice) is required to build PDF/DOC samples")
    subprocess.run([soffice, "--headless", "--convert-to", fmt, "--outdir", str(HERE), str(src)],
                   check=True, capture_output=True, timeout=180)
    return HERE / f"{src.stem}.{fmt}"


def arabic_pdf(src: Path, dst: Path) -> None:
    import html

    from playwright.sync_api import sync_playwright

    lines = [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    body = []
    for i, line in enumerate(lines):
        tag = "h1" if i == 0 else "h2" if ARABIC_HEADING.match(line) else "p"
        body.append(f"<{tag}>{html.escape(line)}</{tag}>")
    page_html = (
        '<html dir="rtl" lang="ar"><body style="font-family:\'DejaVu Sans\';font-size:14px;line-height:1.8">'
        + "".join(body) + "</body></html>"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(page_html)
        page.pdf(path=str(dst), format="A4", margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"})
        browser.close()


def main() -> None:
    # English book with chapters -> DOCX (heading styles) + PDF
    text_to_docx(SRC / "coffee_history.md", HERE / "coffee_history.docx")
    convert(HERE / "coffee_history.docx", "pdf")
    # Form-like English report -> TXT + PDF
    shutil.copy(SRC / "inspection_report.txt", HERE / "inspection_report.txt")
    text_to_docx(SRC / "inspection_report.txt", HERE / "_inspection_tmp.docx", title_first_line=False)
    pdf = convert(HERE / "_inspection_tmp.docx", "pdf")
    pdf.rename(HERE / "inspection_report.pdf")
    (HERE / "_inspection_tmp.docx").unlink()
    # Fully vocalized Arabic book -> TXT + DOCX + PDF
    shutil.copy(SRC / "water_ar.txt", HERE / "water_ar.txt")
    text_to_docx(SRC / "water_ar.txt", HERE / "water_ar.docx", rtl=True)
    # LibreOffice writes broken ToUnicode maps for vocalized Arabic, so the Arabic
    # PDF is printed by Chromium instead (what a browser "Save as PDF" produces).
    arabic_pdf(SRC / "water_ar.txt", HERE / "water_ar.pdf")
    # Arabic form -> DOCX + legacy DOC
    text_to_docx(SRC / "employee_form_ar.txt", HERE / "employee_form_ar.docx", rtl=True)
    convert(HERE / "employee_form_ar.docx", "doc")
    print("samples built:", sorted(p.name for p in HERE.iterdir() if p.is_file() and p.suffix != ".py"))


if __name__ == "__main__":
    main()
