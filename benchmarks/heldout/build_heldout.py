"""Build the held-out evaluation corpus (documents the parser was NOT developed on).

    python -m benchmarks.heldout.build_heldout

Writes documents in new styles and formats, plus deliberately broken files,
into benchmarks/heldout/docs/.
"""
from __future__ import annotations

import html
import random
import re
import shutil
from pathlib import Path

import docx
from docx.oxml.ns import qn

HERE = Path(__file__).parent
SRC = HERE / "src"
OUT = HERE / "docs"


def _rtl(p):
    ppr = p._p.get_or_add_pPr()
    ppr.append(ppr.makeelement(qn("w:bidi"), {}))
    for r in p.runs:
        rpr = r._r.get_or_add_rPr()
        rpr.append(rpr.makeelement(qn("w:rtl"), {}))


def bilingual_policy_docx(dst: Path) -> None:
    """HR policy: English + Arabic paragraphs, heading styles and a table."""
    d = docx.Document()
    d.add_heading("Employee Leave Policy / سياسة إجازات الموظفين", level=1)
    sections = [
        ("Annual Leave", "Full-time employees are entitled to 21 working days of paid annual leave per year. "
         "Employees with more than five years of service receive 28 days. Unused leave of up to 10 days can be carried "
         "over to the next year.",
         "يستحق الموظف المتفرغ إجازة سنوية مدفوعة الأجر مدتها واحد وعشرون يوم عمل، وترتفع إلى ثمانية وعشرين يوماً بعد خمس سنوات من الخدمة."),
        ("Sick Leave", "Employees may take up to 14 days of paid sick leave per year. A medical certificate is required "
         "for any absence longer than two consecutive days.",
         "يحق للموظف الحصول على إجازة مرضية مدفوعة الأجر حتى أربعة عشر يوماً في السنة، ويشترط تقديم تقرير طبي إذا زادت مدة الغياب على يومين متتاليين."),
        ("Parental Leave", "Mothers receive 70 days of fully paid maternity leave. Fathers receive 3 days of paid paternity "
         "leave, which must be taken within one month of the birth.",
         "تحصل الأم على إجازة أمومة مدفوعة الأجر بالكامل مدتها سبعون يوماً، ويحصل الأب على إجازة أبوة مدتها ثلاثة أيام."),
        ("Requesting Leave", "Leave requests must be submitted through the HR portal at least two weeks in advance, except "
         "for sick leave and emergencies. The direct manager approves or rejects the request within three working days.",
         "تقدم طلبات الإجازة عبر بوابة الموارد البشرية قبل أسبوعين على الأقل، ويرد المدير المباشر على الطلب خلال ثلاثة أيام عمل."),
    ]
    for title, en, ar in sections:
        d.add_heading(title, level=2)
        d.add_paragraph(en)
        _rtl(d.add_paragraph(ar))
    table = d.add_table(rows=1, cols=3)
    for cell, text in zip(table.rows[0].cells, ["Leave type", "Days per year", "Paid"]):
        cell.text = text
    for row in [("Annual", "21", "Yes"), ("Sick", "14", "Yes"), ("Unpaid", "30", "No")]:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    d.save(dst)


def manual_pdf(src: Path, dst: Path) -> None:
    """Markdown manual printed to PDF by Chromium (real font-size headings)."""
    from playwright.sync_api import sync_playwright

    parts = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(#+)\s+(.*)", line)
        if m:
            parts.append(f"<h{len(m.group(1))}>{html.escape(m.group(2))}</h{len(m.group(1))}>")
        else:
            parts.append(f"<p>{html.escape(line)}</p>")
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.set_content("<html><body style='font-family:DejaVu Sans;font-size:12px'>" + "".join(parts) + "</body></html>")
        page.pdf(path=str(dst), format="A4")
        b.close()


def long_report(dst: Path, chapters: int = 40) -> None:
    """A long multi-chapter document (~12k words) for scale."""
    rnd = random.Random(7)
    topics = ["logistics", "budget", "hiring", "security", "customers", "suppliers", "training", "energy"]
    out = ["Annual Operations Review"]
    for i in range(1, chapters + 1):
        topic = topics[i % len(topics)]
        out.append(f"\nChapter {i}: {topic.title()} review for region {i}\n")
        for _ in range(rnd.randint(2, 6)):
            sents = [f"In region {i} the {topic} team reported metric {rnd.randint(10, 999)} for quarter {rnd.randint(1, 4)}."
                     for _ in range(rnd.randint(3, 8))]
            out.append(" ".join(sents))
    out.append("\nChapter 41: Special findings\n")
    out.append("The audit in region 41 found that the backup generator fuel contract was signed with Delta Fuels at 0.92 dinars per litre.")
    dst.write_text("\n\n".join(out), encoding="utf-8")


def broken_files() -> None:
    (OUT / "edge_empty.txt").write_text("", encoding="utf-8")
    (OUT / "edge_whitespace.txt").write_text("   \n\n\t \n", encoding="utf-8")
    (OUT / "edge_corrupt.pdf").write_bytes(b"%PDF-1.4\n" + bytes(random.Random(1).randrange(256) for _ in range(2000)))
    (OUT / "edge_fake.docx").write_bytes(b"this is not really a zip file")
    (OUT / "edge_one_line.txt").write_text(" ".join(["word"] * 6000), encoding="utf-8")
    (OUT / "edge_unknown.xyz").write_text("hello", encoding="utf-8")
    # image-only PDF (a scanned page has no text layer)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        svg = "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='200'><rect width='400' height='200' fill='#ccc'/></svg>"
        page.set_content(f"<html><body><img src=\"data:image/svg+xml;utf8,{svg}\"></body></html>")
        page.pdf(path=str(OUT / "edge_image_only.pdf"), format="A4")
        b.close()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    shutil.copy(SRC / "ar_law.txt", OUT / "ar_law.txt")
    shutil.copy(SRC / "en_manual.md", OUT / "en_manual.md")
    manual_pdf(SRC / "en_manual.md", OUT / "en_manual.pdf")
    # legacy Windows Arabic encoding
    (OUT / "ar_news_cp1256.txt").write_bytes((SRC / "ar_news.txt").read_text(encoding="utf-8").encode("cp1256"))
    shutil.copy(SRC / "ar_story_vocalized.txt", OUT / "ar_story_vocalized.txt")
    bilingual_policy_docx(OUT / "bilingual_policy.docx")
    long_report(OUT / "long_report.txt")
    broken_files()
    print("held-out corpus:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
