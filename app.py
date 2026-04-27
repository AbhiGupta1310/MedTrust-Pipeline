from __future__ import annotations

"""
Streamlit Dashboard for Data Scraping & Trust Scoring
Interactive web interface to run the pipeline, view results, and analyze trust scores.
Includes real-time progress logging and deep breakdown analysis.
"""

import json
import os
import sys
import time

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="🛡️ AI Trust Pipeline",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #6366f1;
        background: rgba(99, 102, 241, 0.1);
    }
</style>
""", unsafe_allow_html=True)


def load_data():
    output_file = "output/scraped_data.json"
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def get_trust_color(score):
    if score >= 0.8: return "#10b981" # Emerald
    elif score >= 0.6: return "#f59e0b" # Amber
    elif score >= 0.4: return "#f97316" # Orange
    else: return "#ef4444" # Red


def render_header():
    st.markdown('<h1 class="main-header">🛡️ AI Trust Pipeline</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Advanced Fact-Checking & Credibility Analysis System</p>', unsafe_allow_html=True)


def render_overview(data):
    total = len(data)
    blogs = sum(1 for d in data if d.get("source_type") == "blog")
    youtube = sum(1 for d in data if d.get("source_type") == "youtube")
    pubmed = sum(1 for d in data if d.get("source_type") == "pubmed")
    avg_trust = sum(d.get("trust_score", 0) for d in data) / total if total > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📊 Total Sources", total)
    col2.metric("📝 Blogs", blogs)
    col3.metric("🎬 YouTube", youtube)
    col4.metric("🔬 PubMed", pubmed)
    col5.metric("⭐ Avg Trust", f"{avg_trust:.3f}")


def render_trust_chart(data):
    st.subheader("📊 Ecosystem Reliability")
    df = pd.DataFrame([{
        "Source": (d.get("title") or d.get("source_url") or "Unknown Source")[:40],
        "Trust Score": d.get("trust_score", 0),
        "Type": d.get("source_type", "unknown").capitalize(),
    } for d in data])

    colors = [get_trust_color(s) for s in df["Trust Score"]]

    fig = go.Figure(data=[
        go.Bar(
            x=df["Source"],
            y=df["Trust Score"],
            marker_color=colors,
            text=df["Trust Score"].apply(lambda x: f"{x:.3f}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Trust Score: %{y:.3f}<extra></extra>",
        )
    ])

    fig.update_layout(
        yaxis_range=[0, 1.1],
        yaxis_title="Trust Score (0-1)",
        xaxis_title="",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_breakdown_chart(data):
    st.subheader("🔍 Intelligence Breakdown")

    source_options = [f"{d.get('title', d['source_url'][:40])} ({d['source_type']})" for d in data]
    selected_idx = st.selectbox("Select Intelligence Source:", range(len(source_options)),
                                 format_func=lambda i: source_options[i])

    source = data[selected_idx]
    breakdown = source.get("trust_breakdown", {})

    if breakdown:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            categories = []
            scores = []
            for factor, info in breakdown.items():
                if isinstance(info, dict) and "score" in info:
                    categories.append(factor.replace("_", " ").title())
                    scores.append(info["score"])

            if categories:
                fig = go.Figure(data=go.Scatterpolar(
                    r=scores,
                    theta=categories,
                    fill='toself',
                    fillcolor='rgba(99, 102, 241, 0.2)',
                    line=dict(color='#6366f1', width=2),
                    marker=dict(size=8),
                ))

                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 1], gridcolor="rgba(255,255,255,0.1)"),
                        bgcolor="rgba(0,0,0,0)",
                        angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                    ),
                    height=450,
                    margin=dict(t=50, b=50),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8"),
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Detailed Vector Metrics")
            breakdown_df = pd.DataFrame([
                {
                    "Dimension": factor.replace("_", " ").title(),
                    "Magnitude": f"{info['score']:.3f}",
                    "Weight": f"{info['weight']:.2f}",
                }
                for factor, info in breakdown.items()
                if isinstance(info, dict) and "score" in info
            ])
            st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

            hp = breakdown.get("heuristic_quality_penalty", 0)
            lp = breakdown.get("llm_factcheck_penalty", 0)
            
            if hp > 0 or lp > 0:
                st.markdown("---")
                st.markdown("#### ⚠️ Integrity Alerts")
                if hp > 0:
                    st.warning(f"Heuristic Quality Penalty: -{hp:.1%}")
                if lp > 0:
                    st.error(f"LLM Fact-Check Penalty: -{lp:.1%}")
                    st.caption(f"Bias Detected: {breakdown.get('llm_bias_score', 'N/A')} | Fallacy identified: {breakdown.get('llm_fallacy_detected', 'N/A')}")


def render_source_details(data):
    st.subheader("📋 Extended Intelligence Repository")
    for source in data:
        source_icon = {"blog": "📝", "youtube": "🎬", "pubmed": "🔬"}.get(source["source_type"], "📄")
        score = source.get("trust_score", 0)
        
        with st.expander(f"{source_icon} {source.get('title', source['source_url'][:60])} — Score: {score:.3f}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Source Class:** `{source['source_type'].upper()}`")
                st.markdown(f"**Entity/Author:** {source.get('author', 'Unknown')}")
            with col2:
                st.markdown(f"**Language:** {source.get('language', 'N/A')}")
                st.markdown(f"**Publication Date:** {source.get('published_date', 'N/A')}")
            with col3:
                st.markdown(f"**Trust Vector:** `{score:.3f}`")
                st.markdown(f"**Access Point:** [View Source]({source['source_url']})")

            st.markdown("---")
            tabs = st.tabs(["📄 Full Content", "🏷️ Topic Mapping", "📦 Raw Vectors"])
            
            with tabs[0]:
                content = source.get("content", "No content extracted.")
                st.text_area("Content Dump", content, height=300)
            
            with tabs[1]:
                tags = source.get("topic_tags", [])
                if tags:
                    tags_html = " ".join([f'<span style="background:#6366f122; color:#6366f1; padding:5px 12px; border-radius:20px; font-size:0.8rem; border:1px solid #6366f144; margin-right:8px;">{t}</span>' for t in tags])
                    st.markdown(tags_html, unsafe_allow_html=True)
                else:
                    st.caption("No topics mapped.")
            
            with tabs[2]:
                st.json(source.get("trust_breakdown", {}))


def render_single_analysis():
    st.subheader("🔎 Adaptive URL Analysis")
    st.markdown("Paste any URL to trigger the recursive scraping & LLM evaluation engine.")
    
    url = st.text_input("Enter target URL (Blog, YouTube, PubMed):", placeholder="https://...")
    
    if st.button("Initialize Artificial Intelligence Pipeline", type="primary", use_container_width=True):
        if url:
            progress_status = st.status("🚀 Initializing AI Engine...", expanded=True)
            try:
                from main import process_single_url
                
                progress_status.update(label="🛰️ Synchronizing with target source...", state="running")
                
                progress_status.write("📡 Extracting raw metadata and content...")
                result = process_single_url(url)
                
                if result.get("error"):
                    progress_status.update(label="❌ Intelligence Extraction Failed", state="error")
                    st.error(f"Reason: {result['error']}")
                else:
                    progress_status.write("🧠 Mapping semantic topics and language...")
                    progress_status.write("🛡️ Executing LLM Fact-Checking & Bias Analysis...")
                    progress_status.write("⚖️ Balancing heuristic weights for final score...")
                    
                    progress_status.update(label="✅ Analysis Complete!", state="complete")
                    
                    colA, colB = st.columns([1, 2])
                    with colA:
                        st.metric("Final Trust Score", f"{result['trust_score']:.3f}", delta=f"{result['trust_label']}")
                        st.markdown(f"**Integrity Check:** {'Pass' if result['trust_score'] >= 0.6 else 'Warning'}")
                    
                    with colB:
                        st.success(f"**Analysis Result:** {result.get('title', 'Unknown Title')}")
                        st.caption(f"Author/Entity: {result.get('author')}")
                    
                    st.code(json.dumps(result, indent=2, ensure_ascii=False, default=str), language="json")
                    
            except Exception as e:
                progress_status.update(label="💥 Pipeline Crash", state="error")
                st.error(f"Critical System Error: {e}")
        else:
            st.warning("Input required.")


def render_json_viewer(data):
    st.subheader("📄 Intelligence State (JSON)")
    st.json(data)
    st.download_button("⬇️ Export Data Stream", json.dumps(data, indent=2), "ai_intelligence_dump.json", "application/json")


def main():
    render_header()
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 🛠 Navigation")
        page = st.radio("Intelligence Modules", [
            "📊 Executive Dashboard",
            "📋 Intelligence Repository",
            "🔎 Adaptive URL Analysis",
            "📄 Raw Data Stream",
        ])
        
        st.markdown("---")
        st.markdown("### 🧬 AI Architecture")
        st.info("Powered by GPT-4o-mini & Instructor Pydantic Models for deterministic structure.")

    data = load_data()

    if page == "🔎 Adaptive URL Analysis":
        render_single_analysis()
    elif data is None:
        st.warning("No local data stream detected. Please initialize the 'Adaptive URL Analysis' module.")
    else:
        if page == "📊 Executive Dashboard":
            render_overview(data)
            render_trust_chart(data)
            render_breakdown_chart(data)
        elif page == "📋 Intelligence Repository":
            render_source_details(data)
        elif page == "📄 Raw Data Stream":
            render_json_viewer(data)

if __name__ == "__main__":
    main()
