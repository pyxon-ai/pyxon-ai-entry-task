"""Gradio demo for the Pyxon document parser.

    python app.py                      # http://localhost:7860

Environment:
    PYXON_DATA_DIR      where SQLite + Chroma live (default ./data)
    PYXON_EMBEDDER      'hashing' | 'auto' | <sentence-transformers model>
    ANTHROPIC_API_KEY / OPENAI_API_KEY   optional, enables LLM answers
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

import gradio as gr
import pandas as pd

from pyxon_parser import PyxonParser
from pyxon_parser.arabic import diacritic_stats

ROOT = Path(__file__).parent
SAMPLES = ROOT / "samples"
DEFAULT_SAMPLES = ["coffee_history.docx", "inspection_report.txt", "water_ar.txt", "employee_form_ar.docx"]

parser = PyxonParser(data_dir=os.getenv("PYXON_DATA_DIR", ROOT / "data"))

CSS = """
.chunk {border:1px solid var(--border-color-primary); border-radius:8px; padding:10px 12px; margin:8px 0;
        line-height:1.9; font-size:15px; unicode-bidi:plaintext;}
.chunk .meta {font-size:12px; opacity:.7; margin-bottom:4px; direction:ltr; text-align:left;}
.badge {display:inline-block; padding:1px 7px; border-radius:10px; margin-right:4px; font-size:11px;
        background:var(--color-accent-soft); color:var(--body-text-color);}
"""


def _chunk_html(text: str, meta: str) -> str:
    return (f'<div class="chunk"><div class="meta">{meta}</div>'
            f'<div dir="auto">{html.escape(text)}</div></div>')


def load_samples():
    for name in DEFAULT_SAMPLES:
        parser.ingest(SAMPLES / name, replace=False)
    return library_table(), f"Loaded {len(DEFAULT_SAMPLES)} sample documents."


def library_table():
    docs = parser.sql.list_documents()
    return pd.DataFrame(docs) if docs else pd.DataFrame(columns=["id", "filename", "file_type", "language", "strategy"])


def ingest_files(files, strategy):
    if not files:
        return "Upload at least one file.", "", "", library_table()
    reports, chunk_blocks, summary_blocks = [], [], []
    for f in files:
        path = f if isinstance(f, str) else f.name
        try:
            r = parser.ingest(path, strategy=strategy)
        except Exception as exc:  # show parsing errors in the UI rather than crashing
            reports.append(f"### ❌ {Path(path).name}\n{exc}")
            continue
        a = r.analysis
        concepts = ", ".join(t["term"] for t in parser.sql.top_terms(r.document_id, 10))
        dstats = diacritic_stats(" ".join(c.text for c in r.chunks))
        reports.append(
            f"### {r.filename}\n"
            f"| | |\n|---|---|\n"
            f"| Language / direction | **{a.language}** / {a.direction} (Arabic ratio {a.arabic_ratio}) |\n"
            f"| Diacritics | {'yes' if a.has_diacritics else 'no'} — density {a.diacritic_density}, {dstats['total']} marks kept in chunks |\n"
            f"| Detected type | {a.doc_type} — {a.num_headings} headings, {a.num_tokens} tokens |\n"
            f"| **Chunking strategy** | **{a.strategy}** (score {a.strategy_score}) |\n"
            f"| Why | {'; '.join(a.reasons)} |\n"
            f"| Chunks / RAPTOR nodes | {len(r.chunks)} / {len(r.summaries)} |\n"
            f"| Keywords | {', '.join(a.keywords)} |\n"
            f"| Key concepts (graph PageRank) | {concepts} |\n"
            f"| Timings (s) | {', '.join(f'{k} {v}' for k, v in r.timings.items())} |\n\n"
            f"**Summary:** <span dir='auto'>{html.escape(a.summary)}</span>\n"
        )
        for c in r.chunks:
            meta = f"<b>{r.filename}</b> · #{c.index} · {c.strategy} · {c.token_count} tokens" + (
                f" · <span dir='auto'>{html.escape(c.section)}</span>" if c.section else "")
            chunk_blocks.append(_chunk_html(c.text, meta))
        for s in r.summaries:
            meta = f"<b>{r.filename}</b> · RAPTOR level {s.level} · covers chunks {s.children}"
            summary_blocks.append(_chunk_html(s.text, meta))
    return "\n\n".join(reports), "".join(chunk_blocks), "".join(summary_blocks), library_table()


def search(query, mode, k, include_summaries):
    if not query.strip():
        return ""
    results = parser.search(query, k=int(k), mode=mode, include_summaries=include_summaries)
    if not results:
        return "<p>No results. Load the sample documents or upload a file first.</p>"
    out = []
    for i, r in enumerate(results, 1):
        badges = "".join(f'<span class="badge">{name} #{rank}</span>' for name, rank in r.sources.items())
        meta = (f"<b>{i}. {r.filename}</b> · score {r.score} · level {r.level}"
                + (f" · p.{r.page}" if r.page else "")
                + (f" · <span dir='auto'>{html.escape(r.section)}</span>" if r.section else "") + f"<br>{badges}")
        out.append(_chunk_html(r.text, meta))
    return "".join(out)


def ask(question, k):
    if not question.strip():
        return "", ""
    ans = parser.ask(question, k=int(k))
    if ans.route == "sql":
        table = pd.DataFrame(ans.rows).to_markdown(index=False) if ans.rows else "(no rows)"
        return f"**Routed to SQL**\n\n```sql\n{ans.sql}\n```\n\n{table}", ""
    head = "**Answer** (LLM)" if ans.llm_used else "**Answer** (extractive — set ANTHROPIC_API_KEY or OPENAI_API_KEY for LLM answers)"
    ctx = "".join(_chunk_html(c.text, f"[{i}] <b>{c.filename}</b> · level {c.level}")
                  for i, c in enumerate(ans.contexts, 1))
    return f"{head}\n\n<div dir='auto'>{html.escape(ans.answer)}</div>", ctx


def run_sql(sql):
    try:
        rows = parser.sql.run_readonly_query(sql)
        return pd.DataFrame(rows), ""
    except Exception as exc:
        return pd.DataFrame(), f"⚠️ {exc}"


def delete_doc(doc_id):
    try:
        doc_id = int(doc_id or 0)
        doc = parser.sql.get_document(doc_id)
        if doc is None:
            return library_table(), f"⚠️ No document with id {doc_id}. Use an id from the table below."
        parser.delete(doc_id)
        return library_table(), f"Deleted document {doc_id} ({doc['filename']})."
    except Exception as exc:
        return library_table(), f"⚠️ {exc}"


def benchmark_md():
    p = ROOT / "benchmarks" / "results" / "results.md"
    return p.read_text(encoding="utf-8") if p.exists() else "Run `python -m benchmarks.run_benchmark` first."


with gr.Blocks(title="Pyxon AI Document Parser") as demo:
    gr.Markdown(
        "# Pyxon AI — Document Parser for RAG\n"
        "PDF / DOCX / DOC / TXT → content analysis → automatic **fixed** or **dynamic** chunking → "
        "**Chroma** vectors + **SQLite** metadata, knowledge graph and RAPTOR tree → hybrid retrieval and RAG. "
        "Full Arabic support: diacritics are preserved in storage and ignored for matching.\n\n"
        f"Embedder: `{parser.embedder.name}` · LLM: `{parser.rag.llm.model if parser.rag.llm else 'none (extractive answers)'}`"
    )
    status = gr.Markdown()
    with gr.Tab("1 · Parse documents"):
        with gr.Row():
            files = gr.File(label="Upload PDF / DOCX / DOC / TXT", file_count="multiple",
                            file_types=[".pdf", ".docx", ".doc", ".txt", ".md"])
            with gr.Column():
                strategy = gr.Radio(["auto", "fixed", "dynamic"], value="auto", label="Chunking strategy")
                go = gr.Button("Parse & index", variant="primary")
                # the upload box takes multiple files, so each example value must be a list
                gr.Examples([[[str(SAMPLES / n)]] for n in
                             ["water_ar.pdf", "water_ar.txt", "coffee_history.pdf", "employee_form_ar.doc", "inspection_report.pdf"]],
                            inputs=[files], label="Sample files (Arabic with harakat, English, forms)")
        report = gr.Markdown()
        with gr.Accordion("Chunks", open=True):
            chunks_html = gr.HTML()
        with gr.Accordion("RAPTOR summary tree", open=False):
            summaries_html = gr.HTML()
    with gr.Tab("2 · Search"):
        q = gr.Textbox(label="Query (Arabic with or without harakat, or English)", value="سَدُّ مَأْرِبَ")
        with gr.Row():
            mode = gr.Dropdown(["hybrid", "vector", "keyword", "graph"], value="hybrid", label="Retriever", min_width=160)
            k = gr.Slider(1, 10, value=5, step=1, label="Results (k)", min_width=200)
            summ = gr.Checkbox(label="Include RAPTOR summaries", min_width=200)
        sbtn = gr.Button("Search", variant="primary")
        gr.Examples([["سد مأرب"], ["كيف تتكون السحب؟"], ["مهندسة برمجيات"], ["Which forklift failed inspection?"],
                     ["penny universities"]], inputs=[q])
        results = gr.HTML()
    with gr.Tab("3 · Ask (RAG)"):
        question = gr.Textbox(label="Question", value="ما هي علامات الجفاف؟")
        k2 = gr.Slider(1, 10, value=4, step=1, label="Context passages")
        abtn = gr.Button("Ask", variant="primary")
        gr.Examples([["ما هي علامات الجفاف؟"], ["Who banned coffee in Mecca and when?"],
                     ["How many documents are indexed?"], ["Which chunking strategy was used?"]], inputs=[question])
        answer = gr.Markdown()
        contexts = gr.HTML()
    with gr.Tab("4 · SQL"):
        sql = gr.Textbox(label="Read-only SELECT", lines=3, value=(
            "SELECT d.filename, d.strategy, COUNT(c.id) AS chunks, ROUND(AVG(c.token_count),1) AS avg_tokens\n"
            "FROM documents d JOIN chunks c ON c.document_id = d.id AND c.level = 0 GROUP BY d.id"))
        qbtn = gr.Button("Run")
        sql_err = gr.Markdown()
        sql_out = gr.Dataframe(wrap=True)
    with gr.Tab("5 · Library"):
        with gr.Row():
            lbtn = gr.Button("Load sample documents")
            del_id = gr.Number(label="Document id to delete", precision=0)
            dbtn = gr.Button("Delete", variant="stop")
        lib = gr.Dataframe(value=library_table, wrap=True)
    with gr.Tab("6 · Benchmarks"):
        gr.Markdown(benchmark_md())

    go.click(ingest_files, [files, strategy], [report, chunks_html, summaries_html, lib])
    sbtn.click(search, [q, mode, k, summ], results)
    q.submit(search, [q, mode, k, summ], results)
    abtn.click(ask, [question, k2], [answer, contexts])
    question.submit(ask, [question, k2], [answer, contexts])
    qbtn.click(run_sql, sql, [sql_out, sql_err])
    lbtn.click(load_samples, None, [lib, status])
    dbtn.click(delete_doc, del_id, [lib, status])
    demo.load(load_samples, None, [lib, status])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)), css=CSS)
