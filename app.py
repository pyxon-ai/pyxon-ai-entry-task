import gradio as gr
import requests
import json
import pandas as pd
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

def upload_files(files):
    if not files:
        return "❌ No files selected"
    
    try:
        file_objects = []
        for file in files:
            file_objects.append(('files', open(file.name, 'rb')))
        
        response = requests.post(f"{API_BASE_URL}/api/v1/chunk", files=file_objects)
        
        for _, file_obj in file_objects:
            file_obj.close()
        
        if response.status_code == 200:
            data = response.json()
            return f"✅ Uploaded {data.get('successful', 0)} files successfully!\n\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        else:
            return f"❌ Error: {response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def semantic_search(query, limit):
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/search/semantic",
            params={"query": query, "limit": limit}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            output = f"🔍 Found {len(results)} results\n\n"
            
            for i, r in enumerate(results, 1):
                output += f"**Result {i}:**\n"
                output += f"- File: {r.get('file_name', 'unknown')}\n"
                output += f"- Relevance Score: {r.get('relevance_score', 0):.3f}\n"
                output += f"- Content: {r.get('content', '')[:200]}...\n\n"
            
            return output
        else:
            return f"❌ Error: {response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def sql_search(content, file_name, strategy, document_id):
    try:
        params = {}
        if content:
            params['content'] = content
        if file_name:
            params['file_name'] = file_name
        if strategy != "All":
            params['strategy'] = strategy
        if document_id:
            params['document_id'] = int(document_id)
        
        if not params:
            return "⚠️ Please provide at least one filter"
        
        response = requests.get(
            f"{API_BASE_URL}/api/v1/search/sql",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            output = f"📊 Found {len(results)} results\n\n"
            
            for i, r in enumerate(results, 1):
                output += f"**Result {i}:**\n"
                output += f"- Content: {r.get('content', '')[:200]}...\n\n"
            
            return output
        else:
            return f"❌ Error: {response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def run_evaluation():
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/evaluate/run")
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            
            output = "✅ Evaluation Completed!\n\n"
            output += f"📊 **Statistics:**\n"
            output += f"- Total Questions: {summary.get('total_questions', 0)}\n"
            output += f"- Pass Rate: {summary.get('pass_rate', 0)}%\n"
            output += f"- Average Overall Score: {summary.get('average_scores', {}).get('overall', 0):.2f}/10\n\n"
            
            avg_scores = summary.get('average_scores', {})
            output += f"**Criteria Scores:**\n"
            output += f"- Relevance: {avg_scores.get('relevance', 0):.2f}/10\n"
            output += f"- Completeness: {avg_scores.get('completeness', 0):.2f}/10\n"
            output += f"- Accuracy: {avg_scores.get('accuracy', 0):.2f}/10\n"
            output += f"- Source Match: {avg_scores.get('source_match', 0):.2f}/10\n"
            
            return output
        else:
            return f"❌ Error: {response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_results():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/evaluate/results")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            rows = []
            for r in results:
                scores = r.get('scores', {})
                rows.append({
                    'Q_ID': r.get('question_id'),
                    'Source': r.get('source_file'),
                    'Relevance': scores.get('relevance', 0),
                    'Completeness': scores.get('completeness', 0),
                    'Accuracy': scores.get('accuracy', 0),
                    'Source Match': scores.get('source_match', 0),
                    'Overall': scores.get('overall', 0)
                })
            
            df = pd.DataFrame(rows)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def list_documents():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/search/documents")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            rows = []
            for r in results:
                rows.append({
                    'ID': r.get('id'),
                    'File Name': r.get('file_name'),
                    'Strategy': r.get('strategy_used'),
                    'Created': r.get('created_at', '')[:19]
                })
            
            df = pd.DataFrame(rows)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

with gr.Blocks(title="AI Parser Evaluation Dashboard", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🔍 AI Parser Evaluation Dashboard")
    gr.Markdown("Hybrid-Cloud RAG System with LLM-as-Judge Evaluation")
    
    with gr.Tabs():
        with gr.Tab("📤 Upload Documents"):
            gr.Markdown("### Upload Files for Processing")
            upload_input = gr.File(label="Select Files", file_count="multiple")
            upload_btn = gr.Button("Upload & Process", variant="primary")
            upload_output = gr.Textbox(label="Result", lines=10)
            
            upload_btn.click(upload_files, inputs=[upload_input], outputs=[upload_output])
        
        with gr.Tab("🔍 Semantic Search"):
            gr.Markdown("### Search using Vector Embeddings + Cohere Rerank")
            search_query = gr.Textbox(label="Query", placeholder="Enter your search query...")
            search_limit = gr.Slider(1, 20, value=5, step=1, label="Number of Results")
            search_btn = gr.Button("Search", variant="primary")
            search_output = gr.Markdown()
            
            search_btn.click(semantic_search, inputs=[search_query, search_limit], outputs=[search_output])
        
        with gr.Tab("📊 SQL Search"):
            gr.Markdown("### Search using SQL Filters")
            with gr.Row():
                sql_content = gr.Textbox(label="Content", placeholder="Search in content...")
                sql_filename = gr.Textbox(label="File Name", placeholder="Filter by file name...")
            with gr.Row():
                sql_strategy = gr.Dropdown(["All", "FIXED", "SEMANTIC"], value="All", label="Strategy")
                sql_doc_id = gr.Textbox(label="Document ID", placeholder="Filter by document ID...")
            sql_btn = gr.Button("Search", variant="primary")
            sql_output = gr.Markdown()
            
            sql_btn.click(
                sql_search,
                inputs=[sql_content, sql_filename, sql_strategy, sql_doc_id],
                outputs=[sql_output]
            )
        
        with gr.Tab("⚙️ Run Evaluation"):
            gr.Markdown("### Run LLM-as-Judge Evaluation")
            gr.Markdown("Evaluates all 15 test questions using Gemini AI as judge")
            eval_btn = gr.Button("▶️ Run Evaluation", variant="primary", size="lg")
            eval_output = gr.Markdown()
            
            eval_btn.click(run_evaluation, outputs=[eval_output])
        
        with gr.Tab("📈 Results"):
            gr.Markdown("### Evaluation Results")
            results_btn = gr.Button("🔄 Refresh Results", variant="secondary")
            results_table = gr.Dataframe()
            
            results_btn.click(get_results, outputs=[results_table])
        
        with gr.Tab("📋 Documents"):
            gr.Markdown("### All Uploaded Documents")
            docs_btn = gr.Button("🔄 Refresh Documents", variant="secondary")
            docs_table = gr.Dataframe()
            
            docs_btn.click(list_documents, outputs=[docs_table])
    
    gr.Markdown("---")
    gr.Markdown("**Note:** Make sure your FastAPI backend is running on `http://localhost:8000`")

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
