import pandas as pd
import matplotlib.pyplot as plt
import inspect
import inspect
from typing import get_origin, get_args, List, Dict, Any
import re
import difflib

########################################################################
df = None

def filter_by_quarter(company: str, quarter: str) -> pd.DataFrame:
    """
    Return rows for a given company and quarter.
    """
    return df[(df['company'] == company) & (df['Quarter'] == quarter)]

def filter_metrics_by_companies_and_quarter(
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


