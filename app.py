import uuid
import streamlit as st
from pyxon_parser.app_state import build_state
from pyxon_parser.embeddings import E5Embedder
from pyxon_parser.pipeline import IngestPipeline
from pyxon_parser.storage import SqlStore, VectorStore
from pyxon_parser.retrieval import HybridRetriever
from pyxon_parser.benchmark import run_benchmark
from pyxon_parser.textnorm import strip_diacritics
from pyxon_parser.benchmark import auto_generate_cases, run_benchmark

st.set_page_config(page_title="Pyxon Entry Task Demo", layout="wide")

st.markdown("""
<style>
.rtl { direction: rtl; unicode-bidi: plaintext; text-align: right; }
.small { font-size: 12px; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def _embedder():
    return E5Embedder(model_name="intfloat/multilingual-e5-small", device="cpu")

def _get_session():
    if "state" not in st.session_state:
        st.session_state.state = build_state(persist=False)
    return st.session_state.state

def _get_objects():
    s = _get_session()
    emb = _embedder()
    sql = SqlStore(s.sqlite_path)
    vdb = VectorStore(s.qdrant_path)
    pipe = IngestPipeline(s.sqlite_path, s.qdrant_path, emb)
    retr = HybridRetriever(sql, vdb, emb)
    return s, sql, vdb, pipe, retr

st.sidebar.title("Controls")
if st.sidebar.button("Reset Session"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

s, sql, vdb, pipe, retr = _get_objects()

st.title("AI Document Parser for RAG (Arabic + Diacritics)")

tab1, tab2, tab3, tab4 = st.tabs(["Ingest", "Search", "Documents", "Benchmark"])

with tab1:
    up = st.file_uploader("Upload PDF / DOCX / TXT", type=["pdf", "docx", "txt"])
    if up is not None:
        b = up.getvalue()
        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("Process", use_container_width=True):
                try:
                    log_lines = []
                    log_box = st.empty()

                    def prog(msg: str):
                        log_lines.append(msg)
                        if len(log_lines) > 200:
                            log_lines[:] = log_lines[-200:]
                        log_box.code("\n".join(log_lines))

                    res = pipe.ingest(up.name, b, progress=prog)
                    st.success(f"Indexed: {res.filename} | strategy={res.strategy} | pages={res.n_pages} | chunks={res.n_chunks} | {res.elapsed_ms}ms")
                    st.session_state.last_doc = res.doc_id
                except Exception as e:
                    st.error(str(e))
        with colB:
            st.markdown("**Tip**")
            st.markdown("Upload Arabic with tashkeel and test search with/without diacritics.")

    if "last_doc" in st.session_state:
        doc_id = st.session_state.last_doc
        docs = {d["doc_id"]: d for d in sql.list_documents()}
        if doc_id in docs:
            d = docs[doc_id]
            st.subheader("Analyzer Output")
            st.json(d["metrics"])
            if "decision" in d["metrics"]:
                st.subheader("Decision")
                st.write(d["metrics"]["decision"])
                if "scores" in d["metrics"]:
                    st.json(d["metrics"]["scores"])
                if "why" in d["metrics"]:
                    st.subheader("Why")
                    for line in d["metrics"]["why"]:
                        st.write(f"- {line}")
                if "signals" in d["metrics"]:
                    with st.expander("Signals (debug)", expanded=False):
                        for sgn in d["metrics"]["signals"]:
                            st.write(sgn)

            st.subheader("Sample Chunks")
            chunks = sql.get_chunks_by_doc(doc_id)[:5]
            for c in chunks:
                txt = c["text_raw"]
                is_ar = c["lang"]["ar_ratio"] > 0.15
                if is_ar:
                    st.markdown(f"<div class='rtl'>{txt}</div>", unsafe_allow_html=True)
                else:
                    st.write(txt)
                st.markdown(f"<div class='small'>chunk_id={c['chunk_id']} | page={c['page_start']} | section={c['section_path']}</div>", unsafe_allow_html=True)
                st.divider()

with tab2:
    q = st.text_input("Query (Arabic/English, with/without diacritics)")
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
    k = col1.slider("k", 1, 15, 5)
    use_vec = col2.toggle("Vector", value=True, key="use_vec_search")
    use_bm = col3.toggle("BM25", value=True, key="use_bm_search")
    dia = col4.toggle("Diacritics-aware", value=True, key="dia_search")
    if col5.button("Search", use_container_width=True) and q.strip():
        hits = retr.search(q, k=k, use_bm25=use_bm, use_vector=use_vec, diacritics_aware=dia)
        if not hits:
            st.warning("No results.")
        for h in hits:
            txt = sql.get_chunk_text(h.chunk_id) or ""
            is_ar = any("\u0600" <= ch <= "\u06FF" for ch in txt[:200])
            st.markdown(f"**{h.chunk_id}**  \nscore={h.score:.6f}")
            if is_ar:
                st.markdown(f"<div class='rtl'>{txt}</div>", unsafe_allow_html=True)
            else:
                st.write(txt)
            st.divider()

with tab3:
    docs = sql.list_documents()
    if not docs:
        st.info("No documents indexed yet.")
    else:
        options = {f"{d['filename']} | {d['doc_id'][:10]} | {d['strategy']}": d["doc_id"] for d in docs}
        sel = st.selectbox("Select document", list(options.keys()))
        doc_id = options[sel]
        d = [x for x in docs if x["doc_id"] == doc_id][0]
        st.json(d)

        chunks = sql.get_chunks_by_doc(doc_id)
        st.write(f"Chunks: {len(chunks)}")
        for c in chunks[:30]:
            txt = c["text_raw"]
            is_ar = c["lang"]["ar_ratio"] > 0.15
            if is_ar:
                st.markdown(f"<div class='rtl'>{txt}</div>", unsafe_allow_html=True)
            else:
                st.write(txt)
            st.markdown(f"<div class='small'>chunk_id={c['chunk_id']} | page={c['page_start']} | section={c['section_path']}</div>", unsafe_allow_html=True)
            st.divider()
with tab4:
    st.subheader("Benchmark")

    docs = sql.list_documents()
    if not docs:
        st.info("Index at least one document first.")
    else:
        doc_map = {f"{d['filename']} | {d['doc_id'][:10]}": d["doc_id"] for d in docs}
        sel_doc = st.selectbox("Document", list(doc_map.keys()), key="bench_doc_sel")
        doc_id = doc_map[sel_doc]

        def _first_words(t: str, n: int = 12) -> str:
            ws = [w for w in (t or "").split() if w.strip()]
            return " ".join(ws[:n]).strip()

        colX, colY = st.columns([1, 1])
        with colX:
            if st.button("Auto-generate cases for this document", use_container_width=True, key="auto_cases_btn"):
                chs = sql.get_chunks_by_doc(doc_id)
                if chs:
                    best = sorted(chs, key=lambda x: (x["lang"]["dia_ratio"], x["lang"]["ar_ratio"], -x["chunk_index"]), reverse=True)[0]
                    q1 = _first_words(best["text_raw"], 12)
                    q2 = _first_words(strip_diacritics(best["text_raw"]), 12)
                    if q1:
                        sql.add_benchmark_case(str(uuid.uuid4()), doc_id, q1, [best["chunk_id"]], "auto: excerpt with diacritics")
                    if q2 and q2 != q1:
                        sql.add_benchmark_case(str(uuid.uuid4()), doc_id, q2, [best["chunk_id"]], "auto: excerpt without diacritics")
                    st.success("Generated cases")
                    st.rerun()
                else:
                    st.error("No chunks for this document")
        with colY:
            st.write("")

        st.divider()
        st.subheader("Add Case")

        q_case = st.text_input("Query", key="bench_query")
        notes = st.text_input("Notes", value="", key="bench_notes")

        colA, colB, colC, colD = st.columns([1, 1, 1, 1])
        k_suggest = colA.slider("Suggest k", 3, 20, 10, key="bench_suggest_k")
        dia_case = colB.toggle("Diacritics-aware (suggest)", value=True, key="dia_bench_suggest")
        do_suggest = colC.button("Suggest", use_container_width=True, key="bench_suggest_btn")
        auto_top1 = colD.button("Save with top-1 as gold", use_container_width=True, key="bench_top1_btn")

        gold = set()

        hits = []
        if q_case.strip() and (do_suggest or auto_top1):
            hits = retr.search(q_case, k=k_suggest, use_bm25=True, use_vector=True, diacritics_aware=dia_case)

        if auto_top1 and q_case.strip():
            if hits:
                top_id = getattr(hits[0], "chunk_id", None) if hits else None
                if top_id is None and hits and isinstance(hits[0], dict):
                    top_id = hits[0].get("chunk_id") or (hits[0].get("payload") or {}).get("chunk_id")
                st.success("Saved case (top-1 gold)")
                st.rerun()
            else:
                st.error("No hits to use as gold")

        if do_suggest and q_case.strip():
            st.write("Mark gold from suggested hits:")
            for h in hits:
                txt = sql.get_chunk_text(h.chunk_id) or ""
                label = f"{h.chunk_id} | score={h.score:.4f}"
                if st.checkbox(label, key=f"bench_suggest_gold_{h.chunk_id}"):
                    gold.add(h.chunk_id)
                if txt:
                    is_ar = any("\u0600" <= ch <= "\u06FF" for ch in txt[:150])
                    if is_ar:
                        st.markdown(f"<div class='rtl'>{txt[:450]}</div>", unsafe_allow_html=True)
                    else:
                        st.write(txt[:450])
                st.divider()

        with st.expander("Browse chunks (manual)", expanded=False):
            chs = sql.get_chunks_by_doc(doc_id)
            for c in chs[:80]:
                label = f"{c['chunk_id']} | p{c['page_start']} | {c['section_path']}"
                if st.checkbox(label, key=f"bench_browse_gold_{c['chunk_id']}"):
                    gold.add(c["chunk_id"])

        st.write(f"Gold selected: {len(gold)}")

        if st.button("Save Case", use_container_width=True, key="bench_save_btn"):
            if not q_case.strip():
                st.error("Query is required")
            elif len(gold) == 0:
                st.error("Select at least 1 gold chunk (or use 'Save with top-1 as gold')")
            else:
                sql.add_benchmark_case(str(uuid.uuid4()), doc_id, q_case.strip(), sorted(list(gold)), notes)
                st.success("Saved case")
                st.rerun()

        st.divider()
        st.subheader("Cases")
        cases = sql.list_benchmark_cases()
        if not cases:
            st.write("No cases yet.")
        else:
            for c in cases[:30]:
                st.markdown(f"**{c['case_id']}**  \nDoc: `{c['doc_id'][:10]}`  \nQuery: {c['query']}  \nGold: {len(c['gold'])}  \nNotes: {c['notes']}")
                if st.button("Delete Case", key=f"del_{c['case_id']}"):
                    sql.delete_benchmark_case(c["case_id"])
                    st.rerun()
                st.divider()

        st.subheader("Run")
        col1, col2, col3 = st.columns([1, 1, 1])
        kk = col1.slider("k", 1, 10, 5, key="bench_k")
        dia_run = col2.toggle("Diacritics-aware (run)", value=True, key="dia_bench_run")
        if col3.button("Run Benchmark", use_container_width=True, key="bench_run_btn"):
            res = run_benchmark(retr, sql, k=kk, diacritics_aware=dia_run, doc_id=doc_id)
            st.session_state.bench = res

        st.subheader("Last Run")
        if "bench" in st.session_state:
            st.json(st.session_state.bench)
        else:
            st.write("Run benchmark after saving at least one case.")
