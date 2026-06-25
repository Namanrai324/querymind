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
            "summary": summary,
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": df.columns.tolist(),
            "missing": int(df.isnull().sum().sum())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/chat")
async def chat(req: ChatRequest):
    if not state["agent"]:
        return {"answer": "Please upload a CSV file first."}
    try:
        tools_map = {t.name: t for t in state["tools"]}
        response = state["agent"].invoke(
            {"input": req.message, "agent_scratchpad": []},
            config={"configurable": {"session_id": "main"}}
        )
        final_answer = ""
        if hasattr(response, 'tool_calls') and response.tool_calls:
            from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage
            from langchain_groq import ChatGroq
            tool_messages = []
            for tc in response.tool_calls:
                if tc['name'] in tools_map:
                    result = tools_map[tc['name']].invoke(tc['args'])
                    tool_messages.append(ToolMessage(content=str(result), tool_call_id=tc['id']))
            llm2 = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
            final = llm2.invoke(
                [SystemMessage(content="You are a helpful data analyst. Answer clearly and concisely.")]
                + [HumanMessage(content=req.message)]
                + [response] + tool_messages
            )
            final_answer = final.content
        else:
            final_answer = response.content if hasattr(response, 'content') else str(response)

        chart_path = None
        if os.path.exists("chart.png"):
            import shutil, time
            chart_copy = f"static/chart_{int(time.time())}.png"
            shutil.copy("chart.png", chart_copy)
            chart_path = "/" + chart_copy
            os.remove("chart.png")

        return {"answer": final_answer, "chart": chart_path}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "chart": None}