# 🛡️ MedTrust Pipeline: Submission Overview

This repository contains a comprehensive implementation of a multi-source data scraping and trust scoring system, designed for high-fidelity health and medical content analysis.

## 📋 Quick Links
- **Source Code**: [scraper/](scraper/), [scoring/](scoring/), [utils/](utils/)
- **Generated Dataset**: [output/scraped_data.json](output/scraped_data.json)
- **Technical Report**: [REPORT.md](REPORT.md)
- **Detailed README**: [README.md](README.md)

---

## 🛠️ Implementation Summary

### 1. Multi-Source Scraper (Task 1)
- **Blogs**: Dual-engine extraction using `newspaper3k` with an LLM fallback for non-standard layouts.
- **YouTube**: Dynamic metadata retrieval via `yt-dlp` and a robust transcript engine that cleans and normalizes captions.
- **PubMed**: Direct integration with the **NCBI Entrez API** to pull MeSH terms, citations, and institutional affiliations.

### 2. Trust Score System (Task 2)
The final **Trust Score (0.0 - 1.0)** is calculated through a hybrid engine:
- **Heuristic Metadata (60%)**: 
    - Author Credibility (25%)
    - Domain Authority (25%)
    - Citation Density (20% - Age Adjusted)
    - Source Recency (15%)
    - Medical Disclosure Presence (15%)
- **Semantic Integrity (40%)**: An LLM-powered check for logical fallacies, unverified medical claims, extreme bias, and evidence quality.

### 3. Key Optimizations
- **Singleton Pattern**: Heavy NLP models (KeyBERT) and LLM clients are lazily loaded once and cached to ensure fast subsequent analysis.
- **Language & Region Detection**: Fully automated detection for international content.
- **MMR Topic Tagging**: Uses Maximal Marginal Relevance to provide diverse and relevant topic tags.

---

## 🚀 How to Run
1. Clone the repo and install dependencies: `pip install -r requirements.txt`.
2. Set your `OPENROUTER_API_KEY` in a `.env` file.
3. Run the pipeline: `python main.py`
4. View the results: `streamlit run app.py`

---
*Submitted as part of the Data Scraping & Trust Scoring Assignment.*
