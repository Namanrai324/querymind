# QueryMind — Agentic Business Intelligence Assistant

<div align="center">

![QueryMind Logo](https://img.shields.io/badge/QueryMind-Agentic%20BI%20Assistant-6C63FF?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyeiIvPjwvc3ZnPg==)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.2-1C3C3C?style=flat-square)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3%2070B-F55036?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-querymind--lclb.onrender.com-6C63FF?style=flat-square)](https://querymind-lclb.onrender.com)

**Ask questions about your data in plain English. No SQL. No Python. No waiting.**

[🔗 Live Demo](https://querymind-lclb.onrender.com) · [📊 Report Bug](https://github.com/Namanrai324/querymind/issues) · [✨ Request Feature](https://github.com/Namanrai324/querymind/issues)

</div>

---

## 📌 Overview

**QueryMind** is a fully agentic business intelligence assistant that transforms how non-technical users interact with data. Upload any CSV or Excel file, ask a question in plain English, and QueryMind autonomously writes and executes Pandas/SQL code, generates charts, spots anomalies, and explains insights — all in seconds.

Built as a major project demonstrating real-world agentic AI systems, QueryMind bridges the gap between raw data and business decisions without requiring any SQL or Python knowledge from the end user.

> *"Business teams wait days for analyst bandwidth on simple data questions. QueryMind answers them in under 30 seconds."*

---

## 🎯 Problem Statement

In most organizations:
- Business analysts spend 60–70% of their time on repetitive data extraction and reporting
- Non-technical stakeholders cannot self-serve insights from raw data files
- Ad-hoc data questions require hours of back-and-forth with data teams
- Small companies and startups cannot afford dedicated BI tooling

**QueryMind solves all of this** by acting as an always-available AI data analyst that understands business context and delivers answers instantly.

---

## 🚀 Live Demo

**Try it here:** [https://querymind-lclb.onrender.com](https://querymind-lclb.onrender.com)

Upload any CSV file and ask questions like:
- *"Which product category had the highest profit margin last quarter?"*
- *"Show me a bar chart of sales by region"*
- *"Are there any anomalies or business risks in this data?"*
- *"What were the top 5 customers by revenue?"*
- *"Is there a correlation between discount and profit?"*

---

## ✨ Features

### 🧠 Agentic AI Core
- **Autonomous code generation** — LLM writes and executes Pandas/Python code to answer questions
- **Multi-tool agent** — decides whether to run Python analysis, SQL query, or chart generation based on the question
- **Conversation memory** — remembers context across the full session for natural follow-up questions
- **Self-correcting** — handles code errors gracefully and retries with corrected logic

### 📊 Data Analysis Capabilities
- **Natural language querying** — ask any question about your data in plain English
- **SQL mode** — runs SQL queries on uploaded data via SQLite under the hood
- **Auto chart generation** — creates bar charts, line charts, pie charts, scatter plots from plain English requests
- **Statistical analysis** — mean, median, correlations, distributions, outlier detection
- **Business risk detection** — flags anomalies, missing values, data quality issues

### 💼 Business Intelligence
- **KPI dashboard** — live row count, column count, data quality score, insights generated counter
- **Auto data summary** — instant dataset overview on upload (numeric cols, categorical cols, missing data)
- **Suggested questions** — sidebar quick-fire questions based on your uploaded data
- **PDF-ready insights** — conversation can be exported for sharing with stakeholders

### 🎨 UI/UX
- **Premium dark theme** — glassmorphism design with animated particle canvas background
- **Animated feature cards** — horizontal scroll with hover lift and icon rotation
- **Brain + network logo** — custom SVG mark (organic brain + Delaunay-triangulated network nodes)
- **Toast notifications** — real-time upload and error feedback
- **Loading animations** — skeleton states and spinning loader during analysis
- **Responsive** — works on desktop and mobile browsers

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI + Uvicorn | REST API server, file upload endpoint, chat endpoint |
| **Agent Framework** | LangChain | Tool orchestration, agent loop, conversation memory |
| **LLM** | Groq LLaMA 3.3-70B | Brain of the agent — understands questions, writes code |
| **Data Layer** | Pandas + SQLite | CSV/Excel loading, in-memory analysis, SQL queries |
| **Visualization** | Matplotlib | Chart generation from agent-written code |
| **Frontend** | HTML + CSS + Vanilla JS | Premium animated UI, no framework dependencies |
| **Deployment** | Render (Free tier) | Cloud hosting with auto-deploy from GitHub |
| **Version Control** | Git + GitHub | Source control and CI/CD trigger |

---

## 🏗️ System Architecture

```
User uploads CSV
        │
        ▼
   FastAPI /upload
        │
        ├── Pandas loads file
        ├── SQLite stores data  
        ├── Schema extracted → sent to LLM as context
        └── LangChain agent initialized with 4 tools
                │
User asks question
        │
        ▼
   FastAPI /chat
        │
        ▼
   LangChain Agent (LLaMA 3.3-70B via Groq)
        │
        ├── Tool 1: analyze_data   → runs Pandas code
        ├── Tool 2: run_sql_query  → runs SQL on SQLite
        ├── Tool 3: generate_chart → creates Matplotlib chart
        └── Tool 4: get_column_info → gets column stats
                │
                ▼
        Tool result → LLM summarizes → JSON response
                │
                ▼
        Frontend renders answer + chart
```

---

## 📁 Project Structure

```
querymind/
│
├── api.py                  # FastAPI app — /upload and /chat endpoints
├── app.py                  # (Legacy Streamlit version)
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
│
├── agent/
│   ├── core.py             # LangChain agent setup with Groq LLM
│   ├── tools.py            # 4 agent tools: analyze, SQL, chart, column info
│   └── prompts.py          # System prompt for the agent
│
├── utils/
│   ├── data_loader.py      # CSV/Excel loading, schema extraction, SQLite loader
│   └── chart_utils.py      # Chart helper utilities
│
└── static/
    └── index.html          # Full frontend — HTML + CSS + JS (premium dark UI)
```

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.10+
- A free [Groq API key](https://console.groq.com)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/Namanrai324/querymind.git
cd querymind
```

**2. Create and activate virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your API key**

Create a `.env` file in the root folder:
```env
GROQ_API_KEY=your_groq_api_key_here
```

**5. Run the app**
```bash
uvicorn api:app --reload --port 8000
```

**6. Open in browser**
```
http://localhost:8000
```

---

## 🧪 Example Queries to Try

Upload the [Superstore Sales dataset](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final) and try:

| Query | What happens |
|---|---|
| `Summarize this dataset` | Auto overview of rows, cols, data types |
| `Which category has the highest profit?` | Pandas groupby + sort |
| `Show a bar chart of sales by region` | Matplotlib chart generated |
| `What are the top 5 products by revenue?` | SQL query on SQLite |
| `Is there a correlation between discount and profit?` | Statistical analysis |
| `Are there any business risks in this data?` | Anomaly and outlier detection |
| `Now show that as a pie chart` | Follow-up with memory |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend UI |
| `POST` | `/upload` | Upload CSV/Excel, initializes agent |
| `POST` | `/chat` | Send a question, get answer + optional chart |

### POST /upload
```json
// Request: multipart/form-data with file
// Response:
{
  "success": true,
  "summary": "Dataset Overview: 9,994 rows and 21 columns...",
  "rows": 9994,
  "cols": 21,
  "missing": 0,
  "columns": ["Order ID", "Sales", "Profit", ...]
}
```

### POST /chat
```json
// Request:
{ "message": "Which region had the highest sales?" }

// Response:
{
  "answer": "The **West** region had the highest total sales at $725,457...",
  "chart": "/static/chart_1234567890.png"  // null if no chart
}
```

---

## 🚀 Deployment

The app is deployed on **Render** with auto-deploy from GitHub.

Every `git push` to `main` automatically triggers a new deployment.

**Environment Variables required on Render:**
```
GROQ_API_KEY = your_groq_api_key
```

---

## 🔮 Future Roadmap

- [ ] Multi-CSV join and cross-file analysis
- [ ] PDF report export of full conversation
- [ ] Predictive analytics with forecasting charts
- [ ] Natural language dashboard builder
- [ ] User authentication and saved sessions
- [ ] Support for Google Sheets and database connections
- [ ] Voice input for questions

---

## 👨‍💻 About the Developer

**Naman Rai**  
B.Tech — Data Science & Artificial Intelligence  
IIIT Naya Raipur | Graduating August 2026

This project was built as a major capstone demonstrating end-to-end agentic AI system design — from LLM tool orchestration and code execution to frontend UI and cloud deployment.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/naman-rai-634058299/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=flat-square&logo=github)](https://github.com/Namanrai324)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ If you found this useful, please give it a star on GitHub!**

Built with ❤️ by [Naman Rai](https://github.com/Namanrai324)

</div>