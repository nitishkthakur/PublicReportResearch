import os
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
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


####################################################
######## Convert function to documentation #########
####################################################
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





















def concatenate_pdfs_in_folder(folder_path: str) -> BytesIO:
    """
    Reads all PDF files in the given folder, concatenates them, and returns a BytesIO object.
    This can be used as input for LangChain document loaders.
    """
    pdf_writer = PdfWriter()
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    pdf_files.sort()  # Optional: sort files alphabetically

    for pdf_file in pdf_files:
        file_path = os.path.join(folder_path, pdf_file)
        try:
            pdf_reader = PdfReader(file_path)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")



    output_stream = BytesIO()
    pdf_writer.write(output_stream)
    output_stream.seek(0)
    return output_stream