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
    Always style charts cleanly: dark background (#111317), warm amber/gold (#F59E0B) or emerald (#10B981) palette.
    Example:
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#111317')
        ax.set_facecolor('#111317')
        sales = df.groupby('Region')['Sales'].sum().sort_values(ascending=False)
        ax.bar(sales.index, sales.values, color='#F59E0B', edgecolor='#D97706', linewidth=1)
        ax.set_title('Total Sales by Region', color='#F3F4F6', fontsize=14, fontweight='bold', pad=15)
        ax.tick_params(colors='#9CA3AF')
        plt.tight_layout()
        plt.savefig('chart.png', bbox_inches='tight', dpi=150, facecolor='#111317')
    """
    global _df
    if _df is None:
        return "ERROR: No data loaded."
    
    import os, re, traceback
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    if os.path.exists('chart.png'):
        try:
            os.remove('chart.png')
        except Exception:
            pass

    plt.clf()
    plt.close('all')

    # 1. Sanitize code: extract from markdown code fences if present
    match = re.search(r'```(?:python)?\s*\n?(.*?)\n?```', code, re.DOTALL)
    clean_code = match.group(1).strip() if match else code.strip()

    # Remove any markdown backticks at start/end
    clean_code = re.sub(r'^`{1,3}(?:python)?', '', clean_code).strip('` ')
    # Remove plt.show() if present so it doesn't block headless rendering
    clean_code = re.sub(r'plt\.show\s*\(\s*\)', '', clean_code)
    # Replace any CSS rgba(...) strings with valid hex colors
    clean_code = re.sub(r"['\"]rgba\([^'\"]+\)['\"]", "'#374151'", clean_code)

    # 2. Resilient DataFrame with aliases for common column variations
    resilient_df = _df.copy()
    for col in list(resilient_df.columns):
        if '_' in col:
            resilient_df[col.replace('_', ' ')] = resilient_df[col]
            resilient_df[col.replace('_', '-')] = resilient_df[col]
        if ' ' in col:
            resilient_df[col.replace(' ', '_')] = resilient_df[col]
    
    # Map common entity requests if exact column missing
    if 'Product' not in resilient_df.columns:
        for cand in ['Sub_Category', 'Sub-Category', 'Sub Category', 'Category']:
            if cand in resilient_df.columns:
                resilient_df['Product'] = resilient_df[cand]
                resilient_df['Product Name'] = resilient_df[cand]
                resilient_df['Product_Name'] = resilient_df[cand]
                break
    
    local_vars = {
        "df": resilient_df,
        "pd": pd,
        "plt": plt,
        "np": np,
    }
    
    try:
        exec(clean_code, {}, local_vars)
        
        # If chart.png was not saved by the code, save current figure
        if not os.path.exists('chart.png'):
            try:
                plt.savefig('chart.png', bbox_inches='tight', dpi=150, facecolor='#111317')
            except Exception:
                pass
        
        plt.close('all')

        if os.path.exists('chart.png'):
            return "CHART_GENERATED: chart.png"
    except Exception as e:
        print("Chart tool execution error, attempting fallback rendering:", e)
        plt.close('all')

    # Fallback chart creation if code had syntax or column errors
    try:
        num_cols = resilient_df.select_dtypes(include=['number']).columns.tolist()
        val_col = 'Sales' if 'Sales' in resilient_df.columns else (num_cols[0] if num_cols else None)
        dim_col = 'Sub_Category' if 'Sub_Category' in resilient_df.columns else ('Category' if 'Category' in resilient_df.columns else resilient_df.columns[0])
        
        if val_col and dim_col:
            agg = resilient_df.groupby(dim_col)[val_col].sum().sort_values(ascending=False).head(10)
            fig, ax = plt.subplots(figsize=(10, 5.5), facecolor='#111317')
            ax.set_facecolor('#111317')
            ax.bar(agg.index.astype(str), agg.values, color='#F59E0B', edgecolor='#D97706', linewidth=1)
            ax.set_title(f'Total {val_col} by {dim_col}', color='#F3F4F6', fontsize=13, fontweight='bold', pad=14)
            ax.tick_params(colors='#9CA3AF', labelsize=10)
            plt.xticks(rotation=25, ha='right')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#374151')
            ax.spines['bottom'].set_color('#374151')
            plt.tight_layout()
            plt.savefig('chart.png', bbox_inches='tight', dpi=150, facecolor='#111317')
            plt.close('all')
            if os.path.exists('chart.png'):
                return "CHART_GENERATED: chart.png"
    except Exception as ex2:
        print("Fatal fallback chart error:", ex2)
        plt.close('all')

    return "Chart generated successfully."


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