import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime

st.set_page_config(
    page_title="AI Parser Evaluation Dashboard",
    page_icon="🔍",
    layout="wide"
)

API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

st.title("🔍 AI Parser Evaluation Dashboard")
st.markdown("---")

@st.cache_data(ttl=60)
def fetch_results():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/evaluate/results")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching results: {e}")
        return None

def run_evaluation():
    with st.spinner("Running evaluation... This may take a few minutes..."):
        try:
            response = requests.post(f"{API_BASE_URL}/api/v1/evaluate/run")
            if response.status_code == 200:
                st.success("✅ Evaluation completed successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error running evaluation: {e}")

tabs = st.tabs(["📊 Overview", "📋 Detailed Results", "📈 Analytics", "⚙️ Run Evaluation"])

results = fetch_results()

if results and "error" not in results:
    stats = results.get("statistics", {})
    
    with tabs[0]:
        st.header("Overall Performance")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Questions",
                stats.get("total_questions", 0)
            )
        
        with col2:
            st.metric(
                "Average Score",
                f"{stats.get('average_scores', {}).get('overall', 0):.2f}/10",
                delta=None
            )
        
        with col3:
            st.metric(
                "Pass Rate",
                f"{stats.get('pass_rate', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                "Passed",
                f"{stats.get('pass_count', 0)}/{stats.get('total_questions', 0)}"
            )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Score Distribution")
            
            scores_data = []
            for r in results.get("results", []):
                scores_data.append({
                    "Question ID": r["question_id"],
                    "Score": r["scores"]["overall"]
                })
            
            df_scores = pd.DataFrame(scores_data)
            
            fig = px.histogram(
                df_scores,
                x="Score",
                nbins=10,
                title="Distribution of Overall Scores",
                labels={"Score": "Overall Score (0-10)"},
                color_discrete_sequence=["#1f77b4"]
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Pass/Fail Distribution")
            
            pass_count = stats.get("pass_count", 0)
            fail_count = stats.get("total_questions", 0) - pass_count
            
            fig = go.Figure(data=[go.Pie(
                labels=["Pass (≥7)", "Fail (<7)"],
                values=[pass_count, fail_count],
                marker=dict(colors=["#28a745", "#dc3545"])
            )])
            fig.update_layout(title="Pass/Fail Ratio")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Average Scores by Criteria")
        
        avg_scores = stats.get("average_scores", {})
        criteria_df = pd.DataFrame({
            "Criterion": ["Relevance", "Completeness", "Accuracy", "Source Match"],
            "Score": [
                avg_scores.get("relevance", 0),
                avg_scores.get("completeness", 0),
                avg_scores.get("accuracy", 0),
                avg_scores.get("source_match", 0)
            ]
        })
        
        fig = px.bar(
            criteria_df,
            x="Criterion",
            y="Score",
            title="Average Scores by Evaluation Criteria",
            color="Score",
            color_continuous_scale="Blues",
            range_y=[0, 10]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[1]:
        st.header("Detailed Question Results")
        
        source_filter = st.multiselect(
            "Filter by Source File",
            options=list(set([r["source_file"] for r in results.get("results", [])])),
            default=None
        )
        
        score_range = st.slider(
            "Filter by Score Range",
            min_value=0.0,
            max_value=10.0,
            value=(0.0, 10.0),
            step=0.5
        )
        
        filtered_results = results.get("results", [])
        
        if source_filter:
            filtered_results = [r for r in filtered_results if r["source_file"] in source_filter]
        
        filtered_results = [
            r for r in filtered_results 
            if score_range[0] <= r["scores"]["overall"] <= score_range[1]
        ]
        
        for result in filtered_results:
            with st.expander(f"Q{result['question_id']}: {result['question'][:100]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Question:** {result['question']}")
                    st.markdown(f"**Expected Source:** `{result['source_file']}`")
                    st.markdown(f"**Retrieved Chunks:** {result['retrieved_chunks']}")
                
                with col2:
                    scores = result["scores"]
                    st.metric("Overall Score", f"{scores['overall']}/10")
                    st.metric("Relevance", f"{scores['relevance']}/10")
                    st.metric("Completeness", f"{scores['completeness']}/10")
                    st.metric("Accuracy", f"{scores['accuracy']}/10")
                    st.metric("Source Match", f"{scores['source_match']}/10")
                
                st.markdown("**Judge Reasoning:**")
                st.info(result["scores"].get("reasoning", "N/A"))
                
                st.markdown("**Retrieved Chunks:**")
                for i, chunk in enumerate(result.get("chunks", [])[:3]):
                    st.markdown(f"*Chunk {i+1}* (from: `{chunk.get('file_name', 'unknown')}`)")
                    st.code(chunk["content"][:300] + "..." if len(chunk["content"]) > 300 else chunk["content"])
    
    with tabs[2]:
        st.header("Analytics by Source File")
        
        file_stats = stats.get("by_file", {})
        
        if file_stats:
            file_df = pd.DataFrame([
                {
                    "File": file,
                    "Questions": data["count"],
                    "Average Score": data["average"],
                    "Min Score": data["min"],
                    "Max Score": data["max"]
                }
                for file, data in file_stats.items()
            ])
            
            fig = px.bar(
                file_df,
                x="File",
                y="Average Score",
                title="Average Score by Source File",
                color="Average Score",
                color_continuous_scale="RdYlGn",
                range_y=[0, 10]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(file_df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Score Trends")
        
        trends_data = []
        for r in results.get("results", []):
            trends_data.append({
                "Question ID": r["question_id"],
                "Relevance": r["scores"]["relevance"],
                "Completeness": r["scores"]["completeness"],
                "Accuracy": r["scores"]["accuracy"],
                "Source Match": r["scores"]["source_match"]
            })
        
        trends_df = pd.DataFrame(trends_data)
        
        fig = go.Figure()
        for col in ["Relevance", "Completeness", "Accuracy", "Source Match"]:
            fig.add_trace(go.Scatter(
                x=trends_df["Question ID"],
                y=trends_df[col],
                mode='lines+markers',
                name=col
            ))
        
        fig.update_layout(
            title="Scores by Question",
            xaxis_title="Question ID",
            yaxis_title="Score (0-10)",
            yaxis_range=[0, 10]
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Export Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            results_json = json.dumps(results, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Download Full Results (JSON)",
                data=results_json,
                file_name=f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            summary_df = pd.DataFrame([
                {
                    "Q_ID": r["question_id"],
                    "Source": r["source_file"],
                    "Relevance": r["scores"]["relevance"],
                    "Completeness": r["scores"]["completeness"],
                    "Accuracy": r["scores"]["accuracy"],
                    "Source_Match": r["scores"]["source_match"],
                    "Overall": r["scores"]["overall"]
                }
                for r in results.get("results", [])
            ])
            
            csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Summary (CSV)",
                data=csv,
                file_name=f"evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

with tabs[3]:
    st.header("Run New Evaluation")
    
    st.markdown("""
    Click the button below to run a fresh evaluation on all 15 test questions.
    
    This will:
    - Search for relevant chunks using semantic search
    - Use Gemini to judge retrieval quality
    - Generate comprehensive statistics
    - Save results for visualization
    
    **Note:** This may take several minutes to complete.
    """)
    
    if st.button("▶️ Run Evaluation", type="primary"):
        run_evaluation()
    
    st.markdown("---")
    
    if results:
        st.success(f"Last evaluation run: {results.get('timestamp', 'Unknown')}")
        st.info(f"Total questions evaluated: {results.get('total_questions', 0)}")

    else:
        st.warning("⚠️ No evaluation results found. Run an evaluation first!")
    
    if st.button("▶️ Run First Evaluation", type="primary"):
        run_evaluation()
