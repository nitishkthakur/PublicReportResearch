import pandas as pd
import matplotlib.pyplot as plt

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

def register_functions(func_list: list) -> dict:
    """
    Accepts a list of functions and returns a dict mapping
    function names to the function objects.
    """
    return {fn.__name__: fn for fn in func_list}



