import pandas as pd
import matplotlib.pyplot as plt
import inspect
import inspect
from typing import get_origin, get_args, List, Dict, Any
import re

########################################################################
df = None

def filter_by_quarter(company: str, quarter: str) -> pd.DataFrame:
    """
    Return rows for a given company and quarter.
    """
    return df[(df['company'] == company) & (df['Quarter'] == quarter)]

