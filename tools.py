import pandas as pd
import matplotlib.pyplot as plt
import inspect
import inspect
from typing import get_origin, get_args, List, Dict, Any
import re
import difflib

########################################################################
df = None

def get_available_metrics():
    return df.columns.tolist()

# decorator to apply to a function which returns a dataframe to make it return a json object
def to_json(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).to_json()
    return wrapper

@to_json
def filter_by_quarter(company: str, quarter: str) -> pd.DataFrame:
    """
    Return rows for a given company and quarter.
    """
    return df[(df['company'] == company) & (df['Quarter'] == quarter)]

@to_json
def compare_companies(
    data: pd.DataFrame,
    companies: List[str],
    quarter: str,
    metrics: List[str]
) -> pd.DataFrame:
    """
    Filters a financial DataFrame to extract specific metrics for selected companies in a given quarter.
    This function supports LLM-based financial analysis by enabling targeted extraction of earnings metrics
    from top US financial firms, mapping requested metrics to the closest available ones even when exact
    metric names aren't provided.
    
    Args:
        data: DataFrame containing financial data with columns for date, Company, and 50+ metrics.
        companies: List of company names to include in the filtered result.
        quarter: String representing the quarter to filter by (format: '1Q2025').
        metrics: List of metric names to include in the result, which will be mapped to closest matches.
    """
    global available_metrics  # Assume this is defined elsewhere
    
    # Map each requested metric to its closest match using Levenshtein distance
    def find_closest_metric(metric: str) -> str:
        if metric in available_metrics:
            return metric
        
        matches = difflib.get_close_matches(metric, available_metrics, n=1, cutoff=0.0)
        return matches[0] if matches else metric
    
    # Map requested metrics to their closest matches
    mapped_metrics = [find_closest_metric(m) for m in metrics]
    
    # Filter the DataFrame
    filtered_df = data[
        (data['Company'].isin(companies)) & 
        (data['date'] == quarter)
    ]
    
    # Select only the requested columns
    result_columns = ['Company', 'date'] + mapped_metrics
    return filtered_df[result_columns]

@to_json
def compare_within_one_company(
    data: pd.DataFrame,
    company: str,
    quarters: List[str],
    metrics: List[str]
) -> pd.DataFrame:
    """
    Filters a financial DataFrame to extract specific metrics for a single company across multiple quarters.
    This function enables detailed trend analysis of a company's financial performance over time by mapping
    requested metrics to the closest available ones in the dataset, even when exact metric names aren't provided.
    
    Args:
        data: DataFrame containing financial data with columns for date, Company, and 50+ metrics.
        company: Name of the company to include in the filtered result.
        quarters: List of quarter strings to filter by (format: e.g., '1Q2025', '2Q2025').
        metrics: List of metric names to include in the result, which will be mapped to closest matches.
    """
    global available_metrics  # Assume this is defined elsewhere
    
    # Map each requested metric to its closest match using Levenshtein distance
    def find_closest_metric(metric: str) -> str:
        if metric in available_metrics:
            return metric
        
        matches = difflib.get_close_matches(metric, available_metrics, n=1, cutoff=0.0)
        return matches[0] if matches else metric
    
    # Map requested metrics to their closest matches
    mapped_metrics = [find_closest_metric(m) for m in metrics]
    
    # Filter the DataFrame
    filtered_df = data[
        (data['Company'] == company) & 
        (data['date'].isin(quarters))
    ]
    
    # Select only the requested columns
    result_columns = ['Company', 'date'] + mapped_metrics
    return filtered_df[result_columns]


