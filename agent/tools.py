import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sqlite3
import traceback
from langchain.tools import tool

# ── Global state ──────────────────────────────────────────────────────────────
_df = None
_db_path = None

def set_dataframe(df: pd.DataFrame, db_path: str = None):
    """Call this when user uploads a new file."""
    global _df, _db_path
    _df = df
    _db_path = db_path


# ── Tool 1: Run Pandas code ───────────────────────────────────────────────────
@tool
def analyze_data(code: str) -> str:
    """
    Use this to analyze data using Python and Pandas.
    The dataframe is available as variable 'df'.
    Always store your final answer in a variable called 'result'.
    Example:
        result = df.groupby('Region')['Sales'].sum().sort_values(ascending=False)
    """
    global _df
    if _df is None:
        return "ERROR: No data loaded. Please ask the user to upload a CSV file."
    
    local_vars = {
        "df": _df.copy(),
        "pd": pd,
        "result": None
    }
    
    try:
        exec(code, {}, local_vars)
        result = local_vars.get("result", None)
        
        if result is None:
            return "Code ran but no 'result' variable was set. Please set result = your answer"
        
        if isinstance(result, pd.DataFrame):
            return result.to_string(max_rows=30)
        elif isinstance(result, pd.Series):
            return result.to_string(max_rows=30)
        else:
            return str(result)
    
    except Exception as e:
        return f"Code error: {str(e)}\n{traceback.format_exc()}"


# ── Tool 2: Run SQL queries ───────────────────────────────────────────────────
@tool
def run_sql_query(query: str) -> str:
    """
    Use this to run SQL queries on the uploaded data.
    The table name is 'data'. Use standard SQL syntax.
    Example:
        SELECT Region, SUM(Sales) as total_sales
        FROM data
        GROUP BY Region
        ORDER BY total_sales DESC
    """
    global _db_path
    if _db_path is None:
        return "ERROR: No database loaded. Please ask the user to upload a CSV file."
    
    try:
        conn = sqlite3.connect(_db_path)
        result_df = pd.read_sql_query(query, conn)
        conn.close()
        return result_df.to_string(max_rows=30)
    except Exception as e:
        return f"SQL error: {str(e)}"


# ── Tool 3: Generate charts ───────────────────────────────────────────────────
@tool
def generate_chart(code: str) -> str:
    """
    Use this to create charts using Matplotlib.
    The dataframe is available as 'df'.
    You MUST end the code with: plt.savefig('chart.png', bbox_inches='tight', dpi=150)
    Example:
        fig, ax = plt.subplots(figsize=(10, 6))
        sales = df.groupby('Region')['Sales'].sum().sort_values(ascending=False)
        ax.bar(sales.index, sales.values, color='steelblue')
        ax.set_title('Total Sales by Region')
        plt.tight_layout()
        plt.savefig('chart.png', bbox_inches='tight', dpi=150)
    """
    global _df
    if _df is None:
        return "ERROR: No data loaded."
    
    plt.clf()
    plt.close('all')
    
    local_vars = {
        "df": _df.copy(),
        "pd": pd,
        "plt": plt,
    }
    
    try:
        exec(code, {}, local_vars)
        import os
        if os.path.exists('chart.png'):
            return "CHART_GENERATED: chart.png"
        else:
            return "Chart not saved. Make sure to call plt.savefig('chart.png') at the end."
    
    except Exception as e:
        return f"Chart error: {str(e)}\n{traceback.format_exc()}"


# ── Tool 4: Get column info ───────────────────────────────────────────────────
@tool
def get_column_info(column_name: str) -> str:
    """
    Get detailed statistics about a specific column.
    Use this before writing analysis code to understand a column better.
    """
    global _df
    if _df is None:
        return "ERROR: No data loaded."
    
    if column_name not in _df.columns:
        available = ', '.join(_df.columns.tolist())
        return f"Column '{column_name}' not found. Available columns: {available}"
    
    col = _df[column_name]
    lines = [f"Column: '{column_name}'", f"Type: {col.dtype}"]
    
    if col.dtype in ['int64', 'float64']:
        lines += [
            f"Min: {col.min()}",
            f"Max: {col.max()}",
            f"Mean: {round(col.mean(), 2)}",
            f"Median: {col.median()}",
            f"Null count: {col.isnull().sum()}"
        ]
    else:
        lines += [
            f"Unique values: {col.nunique()}",
            f"Top 5 values:\n{col.value_counts().head(5).to_string()}",
            f"Null count: {col.isnull().sum()}"
        ]
    
    return "\n".join(lines)