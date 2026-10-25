from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import os
from dotenv import load_dotenv

from agent.core import build_agent
from agent.tools import set_dataframe
from utils.data_loader import load_file, get_schema_info, load_to_sqlite, get_auto_summary

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state
state = {"agent": None, "tools": None, "df": None}

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
        state["df"] = df
        db_path = load_to_sqlite(df)
        set_dataframe(df, db_path=db_path)
        schema = get_schema_info(df)
        agent, tools = build_agent(schema)
        state["agent"] = agent
        state["tools"] = tools
        summary = get_auto_summary(df)
        return {
            "success": True,
            "filename": file.filename,
            "summary": summary,
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": df.columns.tolist(),
            "missing": int(df.isnull().sum().sum())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/load-sample")
async def load_sample():
    try:
        sample_path = "data/sample_sales.csv"
        if not os.path.exists(sample_path):
            return {"success": False, "error": "Sample file not found."}
        df = pd.read_csv(sample_path)
        state["df"] = df
        db_path = load_to_sqlite(df)
        set_dataframe(df, db_path=db_path)
        schema = get_schema_info(df)
        agent, tools = build_agent(schema)
        state["agent"] = agent
        state["tools"] = tools
        summary = get_auto_summary(df)
        return {
            "success": True,
            "filename": "sample_sales_enterprise.csv",
            "summary": summary,
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": df.columns.tolist(),
            "missing": int(df.isnull().sum().sum())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/reset-chat")
async def reset_chat():
    try:
        for f in ["chart.png", "static/chart.png"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if state["df"] is not None:
            schema = get_schema_info(state["df"])
            agent, tools = build_agent(schema)
            state["agent"] = agent
            state["tools"] = tools
        return {"success": True, "message": "Conversation memory reset."}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/schema")
async def get_schema():
    if state["df"] is None:
        return {"success": False, "error": "No dataset loaded."}
    df = state["df"]
    column_meta = []
    for col in df.columns:
        column_meta.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "nulls": int(df[col].isnull().sum()),
            "unique": int(df[col].nunique())
        })
    preview = df.head(10).fillna("").to_dict(orient="records")
    return {
        "success": True,
        "rows": df.shape[0],
        "cols": df.shape[1],
        "columns": column_meta,
        "preview": preview
    }

def run_chart_code_safely(code_str: str, df: pd.DataFrame) -> bool:
    import re
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    if not code_str:
        return False

    plt.clf()
    plt.close('all')

    # Remove code fences and unwanted calls
    clean_code = re.sub(r'```(?:python)?', '', code_str).replace('```', '')
    clean_code = re.sub(r'plt\.show\s*\(\s*\)', '', clean_code)
    clean_code = re.sub(r"['\"]rgba\([^'\"]+\)['\"]", "'#374151'", clean_code)

    local_vars = {
        "df": df.copy(),
        "pd": pd,
        "plt": plt,
        "np": np
    }

    try:
        exec(clean_code, {}, local_vars)
        if not os.path.exists("chart.png"):
            plt.savefig("chart.png", dpi=150, bbox_inches="tight", facecolor="#111317")
        plt.close('all')
        return os.path.exists("chart.png")
    except Exception as e:
        print("Chart execution error:", e)
        plt.close('all')
def generate_smart_followups(query: str, answer: str, df: pd.DataFrame) -> list:
    import re
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        llm_sug = ChatGroq(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            temperature=0.3,
            api_key=os.getenv("GROQ_API_KEY")
        )
        cols = list(df.columns) if df is not None else []
        prompt = (
            f"User query: '{query}'\n"
            f"Key findings answer: '{answer[:600]}'\n"
            f"Dataset columns: {cols}\n\n"
            "Generate 3 sharp, highly relevant follow-up questions an executive or data analyst would ask next based on this result and the dataset schema. "
            "Questions should directly explore deeper causes, compare segments, or request a relevant visual chart. "
            "Keep each question concise and under 15 words. Format strictly as:\n"
            "- Question 1\n"
            "- Question 2\n"
            "- Question 3"
        )
        resp = llm_sug.invoke([
            SystemMessage(content="You are an expert strategic business intelligence analyst."),
            HumanMessage(content=prompt)
        ])
        raw_lines = resp.content.strip().split("\n")
        clean_lines = []
        for line in raw_lines:
            line_str = line.strip()
            # Remove bullets, numbers, asterisks, brackets, quotes
            cleaned = re.sub(r'^(?:[-•*]|\d+[\.\)]|\[\d+\])\s*', '', line_str)
            cleaned = re.sub(r'^\*{1,2}(.*?)\*{1,2}', r'\1', cleaned).strip('"`* ')
            if cleaned and len(cleaned) > 8 and not cleaned.lower().startswith(('here are', 'follow-up', 'questions', 'based on')):
                clean_lines.append(cleaned)
        if len(clean_lines) >= 2:
            return clean_lines[:3]
    except Exception as e:
        print("Followup generation error:", e)

    # Dynamic schema-aware fallbacks
    q_lower = query.lower()
    cols_map = {c.lower(): c for c in (df.columns if df is not None else [])}
    cat_col = cols_map.get('category') or cols_map.get('product') or cols_map.get('product name') or 'categories'
    reg_col = cols_map.get('region') or cols_map.get('state') or cols_map.get('city') or 'regions'
    prof_col = cols_map.get('profit') or cols_map.get('margin') or 'profit'
    sales_col = cols_map.get('sales') or cols_map.get('revenue') or 'sales'

    if "profit" in q_lower or "loss" in q_lower or "margin" in q_lower:
        return [
            f"Which customer segment or {reg_col} generated the highest {prof_col}?",
            f"Is there a correlation between discount and {prof_col} margin?",
            f"Show a scatter plot of {prof_col} vs {sales_col} across {cat_col}"
        ]
    elif "sales" in q_lower or "revenue" in q_lower:
        return [
            f"Compare {sales_col} performance across different {reg_col}",
            f"What was the monthly {sales_col} trend over time?",
            f"Which {cat_col} had high {sales_col} volume but negative {prof_col}?"
        ]
    elif "region" in q_lower or "city" in q_lower or "state" in q_lower:
        return [
            f"Which {cat_col} sells best in each {reg_col}?",
            f"Show the top 5 locations by total {sales_col} volume",
            f"Plot a comparative bar chart of {reg_col} {prof_col} margins"
        ]
    return [
        f"Show the top 5 {cat_col} by {prof_col} margin",
        f"Are there any outliers or anomalies in {sales_col} or {prof_col}?",
        f"Plot a distribution chart of {sales_col} across {reg_col}"
    ]

@app.post("/chat")
async def chat(req: ChatRequest):
    if not state["agent"]:
        return {"answer": "Please upload a CSV or Excel file first."}
    
    # Remove any stale chart from previous turns
    if os.path.exists("chart.png"):
        try:
            os.remove("chart.png")
        except Exception:
            pass

    try:
        tools_map = {t.name: t for t in state["tools"]}
        response = state["agent"].invoke(
            {"input": req.message, "agent_scratchpad": []},
            config={"configurable": {"session_id": "main"}}
        )
        final_answer = ""
        chart_generated_by_tool = False

        if hasattr(response, 'tool_calls') and response.tool_calls:
            from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage
            from langchain_groq import ChatGroq
            tool_messages = []
            for tc in response.tool_calls:
                if tc['name'] in tools_map:
                    result = tools_map[tc['name']].invoke(tc['args'])
                    if tc['name'] == 'generate_chart' and 'CHART_GENERATED' in str(result):
                        chart_generated_by_tool = True
                    tool_messages.append(ToolMessage(content=str(result), tool_call_id=tc['id']))

            llm2 = ChatGroq(
                model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"), 
                temperature=0, 
                api_key=os.getenv("GROQ_API_KEY")
            )
            final = llm2.invoke(
                [SystemMessage(content=(
                    "You are an executive data analyst. Summarize findings clearly and concisely in plain English. "
                    "NEVER output raw Python, Matplotlib, or Pandas code blocks to the user. "
                    "If a chart was generated, explain what the visual patterns and numbers indicate."
                ))]
                + [HumanMessage(content=req.message)]
                + [response] + tool_messages
            )
            final_answer = final.content
        else:
            final_answer = response.content if hasattr(response, 'content') else str(response)

        # ── SAFETY FALLBACK 1: If model returned XML tool_calls or raw Matplotlib code ──
        import re
        if "<parameter=code>" in final_answer:
            code_match = re.search(r'<parameter=code>(.*?)(?:</parameter>|</tool_call>|$)', final_answer, re.DOTALL)
            if code_match:
                run_chart_code_safely(code_match.group(1), state["df"])
        elif ("plt." in final_answer or "matplotlib" in final_answer or "fig, ax" in final_answer) and not os.path.exists("chart.png"):
            code_match = re.search(r"```(?:python)?\s*(.*?)```", final_answer, re.DOTALL)
            code_to_run = code_match.group(1) if code_match else final_answer
            run_chart_code_safely(code_to_run, state["df"])

        # ── SAFETY FALLBACK 2: If user explicitly asked for a chart but none was created ──
        is_chart_request = any(w in req.message.lower() for w in [
            'chart', 'graph', 'plot', 'visualiz', 'histogram', 'distribution', 'bar chart', 'pie chart', 'scatter'
        ])
        if is_chart_request and not os.path.exists("chart.png") and state["df"] is not None:
            from langchain_groq import ChatGroq
            from langchain_core.messages import SystemMessage, HumanMessage
            llm_coder = ChatGroq(
                model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
                temperature=0,
                api_key=os.getenv("GROQ_API_KEY")
            )
            prompt = (
                f"Given DataFrame 'df' with columns: {list(state['df'].columns)}, "
                f"write Python Matplotlib code to answer: '{req.message}'. "
                "Use facecolor='#111317', colors=['#F59E0B', '#10B981', '#EA580C'], label colors='#F3F4F6'. "
                "End with plt.savefig('chart.png', dpi=150, bbox_inches='tight', facecolor='#111317'). "
                "Output ONLY the python code inside ```python ```."
            )
            code_resp = llm_coder.invoke([SystemMessage(content="You write executable Python Matplotlib scripts."), HumanMessage(content=prompt)])
            code_text = code_resp.content
            run_chart_code_safely(code_text, state["df"])

        # Sanitize final_answer: remove any XML tags, function calls, and raw Python code
        t = re.sub(r'<tool_call>.*?(?:</tool_call>|$)', '', final_answer, flags=re.DOTALL)
        t = re.sub(r'<function=[^>]+>', '', t)
        t = re.sub(r'<parameter=[^>]+>', '', t)
        t = re.sub(r'</parameter>', '', t)
        t = re.sub(r'</tool_call>', '', t)
        t = re.sub(r'```(?:python)?\s*.*?(?:plt\.|matplotlib|savefig).*?```', '', t, flags=re.DOTALL)
        t = t.strip()
        if not t or len(t) < 15:
            final_answer = "Here is the visual breakdown generated from your dataset:"
        else:
            final_answer = t

        # Save and return chart image
        chart_path = None
        if os.path.exists("chart.png"):
            import shutil, time
            chart_copy = f"static/chart_{int(time.time())}.png"
            shutil.copy("chart.png", chart_copy)
            chart_path = "/" + chart_copy
            try:
                os.remove("chart.png")
            except Exception:
                pass
        elif os.path.exists("static/chart.png"):
            import shutil, time
            chart_copy = f"static/chart_{int(time.time())}.png"
            shutil.move("static/chart.png", chart_copy)
            chart_path = "/" + chart_copy

        # Generate smart, highly relevant follow-up questions
        suggestions = generate_smart_followups(req.message, final_answer, state["df"])

        return {
            "answer": final_answer,
            "chart": chart_path,
            "suggestions": suggestions
        }
    except Exception as e:
        import traceback
        print("Chat endpoint error:", traceback.format_exc())
        return {"answer": f"Error: {str(e)}", "chart": None, "suggestions": []}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)