import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from helpers.config import get_settings
from services.weaviate_client import weaviate_client
from services.supabase_client import supabase_client
from controllers.DynamicController import DynamicController
from controllers.DataController import DataController
from services.storage_service import storage_service
import cohere
import google.generativeai as genai
import tempfile

st.set_page_config(
    page_title="AI Parser",
    page_icon="🔍",
    layout="wide"
)

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

EVAL_QUESTIONS = [
    {"id": 1, "source": "الرياضيات.txt", "question": "ما هو الفرق الجوهري الذي ذكره النص بين الرياضيات البحتة والرياضيات التطبيقية، وهل يوجد خط فاصل واضح بينهما؟"},
    {"id": 2, "source": "الرياضيات.txt", "question": "عرف 'نظرية الاحتمال' حسب ما ورد في النص، وما هي القيم الرياضية التي تحدد احتمال حصول أو عدم حصول حدث معين؟"},
    {"id": 3, "source": "قصة قصيرة.txt", "question": "لماذا كان الناس يتجنبون المرور بجانب البيت المهجور في الحارة القديمة بعد الغروب؟"},
    {"id": 4, "source": "قصة متوسطة.txt", "question": "ما هي الجملة الأخيرة التي قالها الأب قبل أن يغادر المنزل في ليلة شتوية ثقيلة، وماذا كانت حالة ساعة الحائط منذ ذلك الحين؟"},
    {"id": 5, "source": "كأس العالم.pdf", "question": "من هي المنتخبات الثلاثة الأكثر تتويجاً بلقب كأس العالم، وكم عدد المرات التي فاز بها كل منتخب؟"},
    {"id": 6, "source": "كأس العالم.pdf", "question": "ما هي السنوات التي ألغيت فيها بطولة كأس العالم في القرن العشرين، وما هو السبب المباشر لهذا الإلغاء؟"},
    {"id": 7, "source": "كأس العالم.pdf", "question": "كم عدد المنتخبات المشاركة في النظام الحالي للبطولة منذ عام 1998، وكيف يتم تقسيمهم؟"},
    {"id": 8, "source": "عشوائي.txt", "question": "ما هو اللقب الذي لقّبه النبي محمد صلى الله عليه وسلم للصحابي أبو عبيدة عامر بن الجراح؟"},
    {"id": 9, "source": "عشوائي.txt", "question": "من هما الرجلان اللذان رضيهما أبو بكر الصديق للمسلمين يوم سقيفة بني ساعدة؟"},
    {"id": 10, "source": "المعادن.docx", "question": "اشرح الفرق بين 'المعدن' و'الصخر' بناءً على المفاهيم الجيولوجية الواردة في النص."},
    {"id": 11, "source": "المعادن.docx", "question": "ماذا تسمى المواد الصلبة الطبيعية التي لا تمتلك بنية بلورية محددة مثل الأوبال، وبماذا تختلف عن النوع المعدني؟"},
    {"id": 12, "source": "الاعراق.txt", "question": "كيف تطور استخدام مصطلح 'العرق' تاريخياً من الإشارة للمتكلمين بلغة مشتركة وصولاً للقرن التاسع عشر؟"},
    {"id": 13, "source": "الاعراق.txt", "question": "ما هو رأي العلماء الحديث في الأساسيات البيولوجية للتصنيفات العرقية؟"},
    {"id": 14, "source": "معاذ بن جبل.txt", "question": "كم كان عمر معاذ بن جبل عندما أسلم، وماذا كان يفعل في مكة بعد فتحها؟"},
    {"id": 15, "source": "معاذ بن جبل.txt", "question": "أين توفي معاذ بن جبل، وفي أي عام هجري، وما هو سبب الوفاة؟"},
]

def evaluate_with_gemini(question: str, source: str, retrieved_chunks: list) -> dict:
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    chunks_text = "\n---\n".join([c.get('content', '')[:500] for c in retrieved_chunks[:3]])
    
    prompt = f"""أنت مُقيّم لجودة استرجاع المعلومات. قيّم مدى صلة النتائج المسترجعة بالسؤال.

السؤال: {question}
المصدر المتوقع: {source}

النتائج المسترجعة:
{chunks_text}

قيّم النتائج وأعطِ:
1. درجة من 1-10 (10 = ممتاز، 1 = غير ذي صلة)
2. هل النتائج من المصدر الصحيح؟ (نعم/لا)
3. هل يمكن الإجابة على السؤال من النتائج؟ (نعم/جزئياً/لا)
4. تعليق موجز

أجب بصيغة JSON فقط:
{{"score": X, "correct_source": "نعم/لا", "answerable": "نعم/جزئياً/لا", "comment": "..."}}"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        return json.loads(result_text)
    except Exception as e:
        return {"score": 0, "correct_source": "خطأ", "answerable": "خطأ", "comment": str(e)}

st.title("🔍 AI Parser")
st.markdown("**Intelligent Document Chunking & Semantic Search**")

tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "🔎 Semantic Search", "📊 SQL Search", "📋 Evaluation"])

with tab1:
    st.header("Upload Documents")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("🚀 Process Files", type="primary"):
        progress = st.progress(0)
        results = []
        
        for idx, file in enumerate(uploaded_files):
            with st.spinner(f"Processing {file.name}..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                        tmp.write(file.read())
                        tmp_path = tmp.name
                    
                    file.seek(0)
                    
                    class MockUploadFile:
                        def __init__(self, file_obj):
                            self.filename = file_obj.name
                            self.content_type = file_obj.type
                            self._file = file_obj
                        
                        async def read(self):
                            return self._file.read()
                    
                    mock_file = MockUploadFile(file)
                    dynamic_controller = DynamicController()
                    
                    import asyncio
                    loop = asyncio.new_event_loop()
                    result = loop.run_until_complete(
                        dynamic_controller.process_document(
                            file=mock_file,
                            chunk_size=500,
                            overlap_size=25
                        )
                    )
                    
                    chunks = result["chunks"]
                    strategy = result["strategy"]
                    
                    storage_result = loop.run_until_complete(
                        storage_service.store_document(
                            file_name=file.name,
                            strategy=strategy,
                            chunks=chunks
                        )
                    )
                    loop.close()
                    
                    results.append({
                        "file": file.name,
                        "strategy": strategy,
                        "chunks": len(chunks),
                        "document_id": storage_result["document_id"],
                        "status": "✅ Success"
                    })
                    
                    os.unlink(tmp_path)
                    
                except Exception as e:
                    results.append({
                        "file": file.name,
                        "status": f"❌ Error: {str(e)}"
                    })
                
                progress.progress((idx + 1) / len(uploaded_files))
        
        st.success(f"Processed {len(uploaded_files)} file(s)")
        st.dataframe(results)

with tab2:
    st.header("Semantic Search")
    
    query = st.text_input("🔍 Enter your search query", placeholder="e.g., What is machine learning?")
    limit = st.slider("Number of results", 1, 20, 5)
    
    if st.button("Search", key="semantic_search"):
        if query:
            with st.spinner("Searching..."):
                try:
                    cohere_client = cohere.Client(settings.COHERE_API_KEY)
                    
                    embedding_response = cohere_client.embed(
                        texts=[query],
                        model='embed-multilingual-v3.0',
                        input_type='search_query',
                        embedding_types=['float']
                    )
                    query_vector = embedding_response.embeddings.float[0]
                    
                    initial_results = weaviate_client.semantic_search(
                        query_vector=query_vector,
                        limit=limit * 2
                    )
                    
                    if initial_results:
                        documents = [r["content"] for r in initial_results]
                        rerank_response = cohere_client.rerank(
                            query=query,
                            documents=documents,
                            model='rerank-multilingual-v3.0',
                            top_n=limit
                        )
                        
                        st.success(f"Found {len(rerank_response.results)} results")
                        
                        for i, result in enumerate(rerank_response.results):
                            original = initial_results[result.index]
                            with st.expander(f"📄 Result {i+1} | Score: {result.relevance_score:.3f} | {original.get('file_name', 'Unknown')}"):
                                st.markdown(f"**Content:**\n{original['content']}")
                                st.markdown(f"**Document ID:** {original.get('document_id')}")
                    else:
                        st.info("No results found")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a search query")

with tab3:
    st.header("SQL Search")
    
    search_type = st.radio("Search by:", ["Document Name", "Document ID"], horizontal=True)
    
    if search_type == "Document Name":
        file_name_filter = st.text_input("File name", placeholder="e.g., report.pdf")
        sql_limit = st.slider("Number of results", 1, 50, 20, key="sql_limit")
        
        if st.button("Search", key="sql_search"):
            if file_name_filter:
                with st.spinner("Searching..."):
                    try:
                        results = supabase_client.search_by_document_name(file_name_filter, sql_limit)
                        
                        if results:
                            st.success(f"Found {len(results)} document(s)")
                            
                            for doc in results:
                                with st.expander(f"📄 {doc.get('file_name', 'Unknown')} (ID: {doc['id']})"):
                                    st.markdown(f"**Strategy:** {doc.get('strategy_used', 'N/A')}")
                                    st.markdown(f"**Created:** {doc.get('created_at', 'N/A')}")
                        else:
                            st.info("No documents found")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a file name")
    
    else:
        doc_id = st.number_input("Document ID", min_value=1, value=1)
        
        if st.button("Search", key="sql_search_id"):
            with st.spinner("Searching..."):
                try:
                    doc = supabase_client.search_by_document_id(doc_id)
                    
                    if doc:
                        st.success(f"Found document: {doc.get('file_name')}")
                        st.markdown(f"**ID:** {doc['id']}")
                        st.markdown(f"**File Name:** {doc.get('file_name', 'N/A')}")
                        st.markdown(f"**Strategy:** {doc.get('strategy_used', 'N/A')}")
                        st.markdown(f"**Created:** {doc.get('created_at', 'N/A')}")
                        
                        st.subheader("Chunks")
                        chunks = supabase_client.get_chunks_by_document(doc_id)
                        st.write(f"Total chunks: {len(chunks)}")
                        
                        for i, chunk in enumerate(chunks):
                            with st.expander(f"Chunk {i+1}"):
                                st.text(chunk.get('content', '')[:500])
                    else:
                        st.info("Document not found")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab4:
    st.header("📋 Retrieval Evaluation")
    st.markdown("**Test the system with 15 predefined questions and evaluate using Gemini AI**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_questions = st.multiselect(
            "Select questions to evaluate:",
            options=[f"Q{q['id']}: {q['question'][:50]}..." for q in EVAL_QUESTIONS],
            default=[]
        )
    with col2:
        run_all = st.button("🚀 Run All 15", type="primary")
    
    if run_all:
        selected_questions = [f"Q{q['id']}: {q['question'][:50]}..." for q in EVAL_QUESTIONS]
    
    if selected_questions and (st.button("▶️ Evaluate Selected") or run_all):
        cohere_client = cohere.Client(settings.COHERE_API_KEY)
        results_data = []
        
        progress = st.progress(0)
        status = st.empty()
        
        for idx, q_label in enumerate(selected_questions):
            q_id = int(q_label.split(":")[0][1:])
            question_data = next(q for q in EVAL_QUESTIONS if q["id"] == q_id)
            
            status.text(f"Evaluating Q{q_id}: {question_data['question'][:40]}...")
            
            try:
                embedding_response = cohere_client.embed(
                    texts=[question_data['question']],
                    model='embed-multilingual-v3.0',
                    input_type='search_query',
                    embedding_types=['float']
                )
                query_vector = embedding_response.embeddings.float[0]
                
                search_results = weaviate_client.semantic_search(
                    query_vector=query_vector,
                    limit=5
                )
                
                evaluation = evaluate_with_gemini(
                    question_data['question'],
                    question_data['source'],
                    search_results
                )
                
                results_data.append({
                    "ID": q_id,
                    "Question": question_data['question'][:50] + "...",
                    "Expected Source": question_data['source'],
                    "Score": evaluation.get('score', 0),
                    "Correct Source": evaluation.get('correct_source', 'N/A'),
                    "Answerable": evaluation.get('answerable', 'N/A'),
                    "Comment": evaluation.get('comment', '')[:100]
                })
                
            except Exception as e:
                results_data.append({
                    "ID": q_id,
                    "Question": question_data['question'][:50] + "...",
                    "Expected Source": question_data['source'],
                    "Score": 0,
                    "Correct Source": "Error",
                    "Answerable": "Error",
                    "Comment": str(e)[:100]
                })
            
            progress.progress((idx + 1) / len(selected_questions))
        
        status.empty()
        
        st.subheader("📊 Evaluation Results")
        
        avg_score = sum(r['Score'] for r in results_data) / len(results_data) if results_data else 0
        correct_sources = sum(1 for r in results_data if r['Correct Source'] == 'نعم')
        answerable = sum(1 for r in results_data if r['Answerable'] == 'نعم')
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Average Score", f"{avg_score:.1f}/10")
        col2.metric("Correct Source", f"{correct_sources}/{len(results_data)}")
        col3.metric("Answerable", f"{answerable}/{len(results_data)}")
        
        st.dataframe(results_data, use_container_width=True)
        
        st.download_button(
            "📥 Download Results (JSON)",
            json.dumps(results_data, ensure_ascii=False, indent=2),
            "evaluation_results.json",
            "application/json"
        )

with st.sidebar:
    st.header("📋 Documents")
    
    if st.button("🔄 Refresh List"):
        st.rerun()
    
    try:
        docs = supabase_client.get_all_documents(limit=20)
        
        if docs:
            for doc in docs:
                st.markdown(f"**{doc.get('file_name', 'Unknown')}**")
                st.caption(f"ID: {doc['id']} | Strategy: {doc.get('strategy_used', 'N/A')}")
                st.divider()
        else:
            st.info("No documents yet")
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

st.markdown("---")
st.caption(f"{settings.APP_NAME} v{settings.APP_VERSION}")
