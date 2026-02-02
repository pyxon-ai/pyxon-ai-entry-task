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
            st.metric("Total Questions", stats.get("total_questions", 0))
        
        with col2:
            st.metric("Average Score", f"{stats.get('average_scores', {}).get('overall', 0):.2f}/10")
        
        with col3:
            st.metric("Pass Rate", f"{stats.get('pass_rate', 0):.1f}%")
        
        with col4:
            st.metric("Passed", f"{stats.get('pass_count', 0)}/{stats.get('total_questions', 0)}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Score Distribution")
            scores_data = [{"Question ID": r["question_id"], "Score": r["scores"]["overall"]} for r in results.get("results", [])]
            df_scores = pd.DataFrame(scores_data)
            fig = px.histogram(df_scores, x="Score", nbins=10, title="Distribution of Overall Scores")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Pass/Fail Distribution")
            pass_count = stats.get("pass_count", 0)
            fail_count = stats.get("total_questions", 0) - pass_count
            fig = go.Figure(data=[go.Pie(labels=["Pass (≥7)", "Fail (<7)"], values=[pass_count, fail_count])])
            st.plotly_chart(fig, use_container_width=True)
    
    with tabs[1]:
        st.header("Detailed Question Results")
        
        for result in results.get("results", []):
            with st.expander(f"Q{result['question_id']}: {result['question'][:80]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Question:** {result['question']}")
                    st.markdown(f"**Expected Source:** `{result['source_file']}`")
                
                with col2:
                    scores = result["scores"]
                    st.metric("Overall Score", f"{scores['overall']}/10")
                    st.metric("Relevance", f"{scores['relevance']}/10")
    
    with tabs[2]:
        st.header("Analytics")
        st.info("Analytics charts and exports available here")
    
with tabs[3]:
    st.header("Run New Evaluation")
    st.markdown("Click the button below to run a fresh evaluation on all 15 test questions.")
    
    if st.button("▶️ Run Evaluation", type="primary"):
        run_evaluation()
