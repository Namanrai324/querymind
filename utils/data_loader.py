import pandas as pd
import sqlite3

def load_file(file) -> pd.DataFrame:
    """Load CSV or Excel file into a Pandas DataFrame."""
    filename = file.name if hasattr(file, 'name') else str(file)
    
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
    else:
        raise ValueError("Only CSV and Excel files are supported.")
    
    return df


def get_schema_info(df: pd.DataFrame) -> str:
    """Extract schema information from the dataframe.
    This is sent to the LLM so it knows what columns exist."""
    lines = []
    lines.append(f"Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns")
    lines.append("")
    lines.append("Column details:")
    
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = df[col].isnull().sum()
        sample_vals = df[col].dropna().head(3).tolist()
        
        if df[col].dtype in ['int64', 'float64']:
            col_min = round(df[col].min(), 2)
            col_max = round(df[col].max(), 2)
            col_mean = round(df[col].mean(), 2)
            lines.append(
                f"  - '{col}' (type: {dtype}, nulls: {null_count}) "
                f"| min={col_min}, max={col_max}, mean={col_mean} "
                f"| samples: {sample_vals}"
            )
        else:
            unique_count = df[col].nunique()
            lines.append(
                f"  - '{col}' (type: {dtype}, nulls: {null_count}, "
                f"unique values: {unique_count}) | samples: {sample_vals}"
            )
    
    return "\n".join(lines)


def load_to_sqlite(df: pd.DataFrame, table_name: str = "data") -> str:
    """Save dataframe to a local SQLite database.
    Returns the database path."""
    db_path = "querymind_temp.db"
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    return db_path


def get_auto_summary(df: pd.DataFrame) -> str:
    """Generate a quick automatic summary of the dataset."""
    lines = []
    lines.append(f"**Dataset Overview**: {df.shape[0]:,} rows and {df.shape[1]} columns")
    
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    
    if numeric_cols:
        lines.append(f"**Numeric columns** ({len(numeric_cols)}): {', '.join(numeric_cols)}")
    if cat_cols:
        lines.append(f"**Categorical columns** ({len(cat_cols)}): {', '.join(cat_cols)}")
    
    null_cols = df.columns[df.isnull().any()].tolist()
    if null_cols:
        lines.append(f"**Columns with missing data**: {', '.join(null_cols)}")
    else:
        lines.append("**Missing data**: None — dataset is complete.")
    
    return "\n".join(lines)