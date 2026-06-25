import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.messages import ToolMessage as LCToolMessage
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from agent.core import build_agent
from agent.tools import set_dataframe, analyze_data, run_sql_query, generate_chart, get_column_info
from utils.data_loader import load_file, get_schema_info, load_to_sqlite, get_auto_summary

load_dotenv()

# ── MUST be first Streamlit command ───────────────────────────────────────────
st.set_page_config(
    page_title="QueryMind",
    page_icon="📊",
    layout="wide"
)

# ── Load custom CSS (after set_page_config) ───────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 QueryMind")
    st.markdown("Upload any CSV and ask questions in plain English.")
    st.divider()

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx", "xls"]
    )

    st.divider()
    st.markdown("**Example questions:**")
    example_questions = [
        "Summarize this dataset",
        "Which category has the highest sales?",
        "Show a bar chart of sales by region",
        "What are the top 5 rows by profit?",
        "Are there any missing values?",
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True):
            st.session_state.pending_question = q

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = None
        st.session_state.tools = None
        st.session_state.df = None
        st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown('<p style="font-family:Space Grotesk,sans-serif;font-size:2rem;font-weight:700;background:linear-gradient(135deg,#F0F4FF,#6C63FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">📊 QueryMind</p>', unsafe_allow_html=True)
st.markdown('<p style="color:rgba(240,244,255,0.5);margin-top:-10px;">Chat with your data — no SQL or Python needed</p>', unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "tools" not in st.session_state:
    st.session_state.tools = None
if "df" not in st.session_state:
    st.session_state.df = None

# ── Handle file upload ────────────────────────────────────────────────────────
if uploaded_file and st.session_state.df is None:
    with st.spinner("Loading your data..."):
        try:
            df = load_file(uploaded_file)
            st.session_state.df = df

            db_path = load_to_sqlite(df)
            set_dataframe(df, db_path=db_path)

            schema = get_schema_info(df)
            agent, tools = build_agent(schema)
            st.session_state.agent = agent
            st.session_state.tools = tools

            summary = get_auto_summary(df)
            welcome = f"File loaded! \n\n{summary}\n\nAsk me anything about your data."
            st.session_state.messages.append({
                "role": "assistant",
                "content": welcome
            })
            st.rerun()

        except Exception as e:
            st.error(f"Failed to load file: {str(e)}")

# ── Data preview ──────────────────────────────────────────────────────────────
if st.session_state.df is not None:
    with st.expander("Preview data", expanded=False):
        df = st.session_state.df
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", f"{df.shape[0]:,}")
        c2.metric("Columns", df.shape[1])
        c3.metric("Missing values", df.isnull().sum().sum())
        st.dataframe(df.head(10), use_container_width=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "chart" in msg and os.path.exists(msg["chart"]):
            st.image(msg["chart"])

# ── Handle pending question from sidebar buttons ──────────────────────────────
user_input = None
if "pending_question" in st.session_state:
    user_input = st.session_state.pending_question
    del st.session_state.pending_question

# ── Chat input ────────────────────────────────────────────────────────────────
if not uploaded_file:
    st.info("Upload a CSV or Excel file from the sidebar to get started.")
else:
    typed = st.chat_input("Ask anything about your data...")
    if typed:
        user_input = typed

# ── Process message ───────────────────────────────────────────────────────────
if user_input and st.session_state.agent:

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                tools_map = {t.name: t for t in st.session_state.tools}

                response = st.session_state.agent.invoke(
                    {"input": user_input, "agent_scratchpad": []},
                    config={"configurable": {"session_id": "main"}}
                )

                final_answer = ""
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    tool_messages = []
                    for tc in response.tool_calls:
                        tool_name = tc['name']
                        tool_args = tc['args']
                        if tool_name in tools_map:
                            result = tools_map[tool_name].invoke(tool_args)
                            tool_messages.append(
                                LCToolMessage(content=str(result), tool_call_id=tc['id'])
                            )

                    llm2 = ChatGroq(
                        model="llama-3.3-70b-versatile",
                        temperature=0,
                        api_key=os.getenv("GROQ_API_KEY")
                    )
                    final = llm2.invoke(
                        [SystemMessage(content="You are a helpful data analyst. Summarize the tool results clearly and concisely.")]
                        + [HumanMessage(content=user_input)]
                        + [response]
                        + tool_messages
                    )
                    final_answer = final.content
                else:
                    final_answer = response.content if hasattr(response, 'content') else str(response)

                st.markdown(final_answer)

                chart_msg = {}
                if os.path.exists("chart.png"):
                    import shutil, time
                    chart_copy = f"chart_{int(time.time())}.png"
                    shutil.copy("chart.png", chart_copy)
                    st.image(chart_copy)
                    chart_msg["chart"] = chart_copy
                    os.remove("chart.png")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer,
                    **chart_msg
                })

            except Exception as e:
                error_msg = f"Something went wrong: {str(e)}"
                st.error(error_msg)