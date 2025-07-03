import pandas as pd
import matplotlib.pyplot as plt
import inspect
import inspect
from typing import get_origin, get_args, List, Dict, Any
import re

# load the only Excel file once
EXCEL_PATH = "/home/nitish/Documents/github/PublicReportResearch/data/financials.xlsx"


def load_financial_excel(sheet_name: str = None) -> pd.DataFrame:
    """
    Read a financial Excel file into a DataFrame.
    - Parses a 'Date' column into datetime.
    - Converts 'Quarter' strings like '1Q2025' into a Timestamp at quarter start.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    if 'Quarter' in df.columns:
        def _q2dt(q: str) -> pd.Timestamp:
            qr, yr = int(q[0]), int(q[2:])
            month = (qr - 1) * 3 + 1
            return pd.Timestamp(year=yr, month=month, day=1)
        df['Quarter_Start'] = df['Quarter'].apply(_q2dt)
    return df

# single DataFrame for all tools
df = load_financial_excel()



#########################################################################

def filter_by_quarter(company: str, quarter: str) -> pd.DataFrame:
    """
    Return rows for a given company and quarter.
    """
    return df[(df['company'] == company) & (df['Quarter'] == quarter)]

def compute_metric_growth(
    metric: str,
    start_quarter: str,
    end_quarter: str,
    company: str
) -> float:
    """
    Compute percentage growth of `metric` for a company between two quarters.
    """
    sub = df[df['company'] == company]
    s = sub.loc[sub['Quarter'] == start_quarter, metric]
    e = sub.loc[sub['Quarter'] == end_quarter, metric]
    if s.empty or e.empty:
        raise ValueError("Company or quarter not found in DataFrame.")
    return (e.iloc[0] - s.iloc[0]) / s.iloc[0] * 100



def top_companies_by_metric(
    metric: str,
    top_n: int = 5,
    quarter: str = None
) -> pd.DataFrame:
    """
    Identify top N companies by metric (optionally filtered to a specific quarter).
    Returns rows for those companies (and quarter if provided).
    """
    subset = df if quarter is None else df[df['Quarter'] == quarter]
    # compute the metric for each company (using max in case of multiple entries)
    company_values = subset.groupby('company')[metric].max()
    top_companies = company_values.nlargest(top_n).index.tolist()
    return subset[subset['company'].isin(top_companies)]


def register_functions(func_list: list) -> dict:
    """
    Accepts a list of functions and returns a dict mapping
    function names to the function objects.
    """
    return {fn.__name__: fn for fn in func_list}




def function_to_tool(fn: Any) -> Dict[str, Any]:
    """
    Convert a single Python function into an Ollama/OpenAI-style tool dictionary,
    including parameter-level documentation extracted from the docstring.
    """
  # Mapping from Python types to JSON Schema types
    _PYTHON_TO_JSON_TYPE = {
        str:   ("string", None),
        int:   ("integer", None),
        float: ("number",  None),
        bool:  ("boolean", None),
    }
    def _map_type(py_type):
        origin = get_origin(py_type)
        if origin in (list, List):
            item_type = get_args(py_type)[0] if get_args(py_type) else str
            return {"type": "array", "items": _map_type(item_type)}
        json_type, fmt = _PYTHON_TO_JSON_TYPE.get(py_type, ("string", None))
        schema = {"type": json_type}
        if fmt:
            schema["format"] = fmt
        return schema

    def _parse_docstring(doc: str):
        if not doc:
            return "", {}
        # Split description and Args section
        parts = re.split(r"\n\s*Args?:\s*", doc, maxsplit=1)
        description = parts[0].strip().split("\n\n")[0].replace("\n", " ")
        params_docs = {}
        if len(parts) > 1:
            # Extract each param line
            args_section = parts[1]
            for line in args_section.splitlines():
                match = re.match(r"\s*(\w+)\s*:\s*(.*)", line)
                if match:
                    param_name, desc = match.groups()
                    params_docs[param_name] = desc.strip()
        return description, params_docs

    sig = inspect.signature(fn)
    properties = {}
    required = []

    description, params_docs = _parse_docstring(fn.__doc__ or "")

    for name, param in sig.parameters.items():
        if param.default is inspect.Parameter.empty:
            required.append(name)
        annotation = param.annotation if param.annotation is not inspect.Parameter.empty else str
        prop_schema = _map_type(annotation)
        # Attach per-parameter description if available
        if name in params_docs:
            prop_schema["description"] = params_docs[name]
        properties[name] = prop_schema

    tool_dict = {
        "name": fn.__name__,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    }
    return tool_dict
