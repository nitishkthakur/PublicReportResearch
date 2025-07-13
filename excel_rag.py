import pandas as pd
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

class FinancialDataTools:
    """
    Tools for querying financial data from Excel files.
    All tools return JSON responses for LLM consumption.
    """
    
    def __init__(self, excel_file_path: str, convert_datetime_to_quarter: bool = True):
        """
        Initialize with Excel file path.
        
        Args:
            excel_file_path: Path to the Excel file containing financial data
            convert_datetime_to_quarter: Whether to convert datetime columns to quarter format
        """
        self.excel_file_path = excel_file_path
        self.convert_datetime_to_quarter = convert_datetime_to_quarter
        self.df = None
        self.load_data()
    
    def _convert_datetime_to_quarter(self, datetime_obj) -> str:
        """
        Convert datetime object to nQYYYY format.
        
        Args:
            datetime_obj: Datetime object or string
            
        Returns:
            String in nQYYYY format (e.g., "4Q2019")
        """
        try:
            if pd.isna(datetime_obj):
                return None
            
            # Convert to datetime if it's a string
            if isinstance(datetime_obj, str):
                dt = pd.to_datetime(datetime_obj)
            else:
                dt = datetime_obj
            
            # Determine quarter
            quarter = (dt.month - 1) // 3 + 1
            year = dt.year
            
            return f"{quarter}Q{year}"
        except:
            return str(datetime_obj)  # Return as-is if conversion fails
    
    def load_data(self) -> None:
        """Load data from Excel file."""
        try:
            self.df = pd.read_excel(self.excel_file_path)
            
            # Handle datetime column conversion
            datetime_col = None
            if 'Datetime' in self.df.columns:
                datetime_col = 'Datetime'
            elif 'Date' in self.df.columns:
                datetime_col = 'Date'
                # Rename Date to Datetime for consistency
                self.df = self.df.rename(columns={'Date': 'Datetime'})
            
            if datetime_col and self.convert_datetime_to_quarter:
                # Convert datetime column to quarter format
                if datetime_col == 'Date':
                    self.df['Datetime'] = self.df['Date'].apply(self._convert_datetime_to_quarter)
                else:
                    self.df['Datetime'] = self.df['Datetime'].apply(self._convert_datetime_to_quarter)
            elif 'Datetime' in self.df.columns:
                # Ensure datetime column is properly formatted as string
                self.df['Datetime'] = self.df['Datetime'].astype(str)
                
        except Exception as e:
            raise Exception(f"Error loading Excel file: {str(e)}")
    
    def _parse_quarter_year(self, date_str: str) -> tuple:
        """
        Parse nQYYYY format to extract quarter and year.
        
        Args:
            date_str: Date string in nQYYYY format (e.g., "1Q2023")
            
        Returns:
            Tuple of (quarter, year)
        """
        pattern = r'(\d)Q(\d{4})'
        match = re.match(pattern, str(date_str))
        if match:
            quarter = int(match.group(1))
            year = int(match.group(2))
            return quarter, year
        return None, None
    
    def _validate_inputs(self, company: str = None, quarter: int = None, 
                        year: int = None, metric: str = None) -> Dict[str, Any]:
        """
        Validate input parameters.
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        if company and company not in self.df['CompanyName'].values:
            available_companies = self.df['CompanyName'].unique().tolist()
            errors.append(f"Company '{company}' not found. Available companies: {available_companies}")
        
        if quarter and (quarter < 1 or quarter > 4):
            errors.append("Quarter must be between 1 and 4")
        
        if year and (year < 1900 or year > 2100):
            errors.append("Year must be a valid 4-digit year")
        
        if metric and metric not in self.df.columns:
            available_metrics = [col for col in self.df.columns if col not in ['Datetime', 'CompanyName']]
            errors.append(f"Metric '{metric}' not found. Available metrics: {available_metrics}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def get_metric_for_company_quarter_year(self, 
                                          company: str, 
                                          metric: str,
                                          quarter: int, 
                                          year: int,
                                          sort_descending: bool = True) -> str:
        """
        Get a specific metric for a company in a specific quarter and year.
        
        Args:
            company: Company name
            metric: Financial metric name
            quarter: Quarter (1-4)
            year: Year (YYYY)
            sort_descending: Whether to sort results in descending order
            
        Returns:
            JSON string with the result
        """
        try:
            # Validate inputs
            validation = self._validate_inputs(company, quarter, year, metric)
            if not validation["valid"]:
                return json.dumps({
                    "success": False,
                    "error": "Validation failed",
                    "details": validation["errors"]
                }, indent=2)
            
            # Filter data
            filtered_df = self.df[self.df['CompanyName'] == company].copy()
            
            # Add parsed quarter and year columns
            filtered_df['Quarter'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[0])
            filtered_df['Year'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[1])
            
            # Filter by quarter and year
            result_df = filtered_df[
                (filtered_df['Quarter'] == quarter) & 
                (filtered_df['Year'] == year)
            ]
            
            if result_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"No data found for {company} in Q{quarter} {year}"
                }, indent=2)
            
            # Get the metric value
            if metric in result_df.columns:
                metric_value = result_df[metric].iloc[0]
                
                return json.dumps({
                    "success": True,
                    "data": {
                        "company": company,
                        "quarter": quarter,
                        "year": year,
                        "metric": metric,
                        "value": float(metric_value) if pd.notna(metric_value) else None,
                        "date": result_df['Datetime'].iloc[0]
                    }
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Metric '{metric}' not found in data"
                }, indent=2)
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error retrieving data: {str(e)}"
            }, indent=2)
    
    def get_metric_trends(self, 
                         company: str, 
                         metric: str,
                         num_quarters: int = 4,
                         sort_descending: bool = True) -> str:
        """
        Get metric trends for a company over multiple quarters.
        
        Args:
            company: Company name
            metric: Financial metric name
            num_quarters: Number of recent quarters to retrieve
            sort_descending: Whether to sort results in descending order by date
            
        Returns:
            JSON string with the trend data
        """
        try:
            # Validate inputs
            validation = self._validate_inputs(company=company, metric=metric)
            if not validation["valid"]:
                return json.dumps({
                    "success": False,
                    "error": "Validation failed",
                    "details": validation["errors"]
                }, indent=2)
            
            # Filter data for the company
            filtered_df = self.df[self.df['CompanyName'] == company].copy()
            
            # Add parsed quarter and year columns
            filtered_df['Quarter'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[0])
            filtered_df['Year'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[1])
            
            # Sort by year and quarter
            filtered_df = filtered_df.sort_values(['Year', 'Quarter'], ascending=not sort_descending)
            
            # Get the most recent quarters
            recent_data = filtered_df.head(num_quarters)
            
            if recent_data.empty:
                return json.dumps({
                    "success": False,
                    "error": f"No data found for {company}"
                }, indent=2)
            
            # Extract trend data
            trend_data = []
            for _, row in recent_data.iterrows():
                trend_data.append({
                    "date": row['Datetime'],
                    "quarter": int(row['Quarter']) if pd.notna(row['Quarter']) else None,
                    "year": int(row['Year']) if pd.notna(row['Year']) else None,
                    "value": float(row[metric]) if pd.notna(row[metric]) else None
                })
            
            return json.dumps({
                "success": True,
                "data": {
                    "company": company,
                    "metric": metric,
                    "num_quarters": len(trend_data),
                    "sorted_descending": sort_descending,
                    "trend": trend_data
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error retrieving trend data: {str(e)}"
            }, indent=2)
    
    def compare_companies_metric(self, 
                               companies, 
                               metric: str,
                               quarter: int, 
                               year: int,
                               sort_descending: bool = True) -> str:
        """
        Compare a specific metric across multiple companies for a given quarter and year.
        
        Args:
            companies: List of company names or comma-separated string of company names
            metric: Financial metric name
            quarter: Quarter (1-4)
            year: Year (YYYY)
            sort_descending: Whether to sort results in descending order by metric value
            
        Returns:
            JSON string with comparison data
        """
        try:
            # Handle both List[str] and comma-separated string inputs
            if isinstance(companies, str):
                companies_list = [company.strip() for company in companies.split(',')]
            elif isinstance(companies, list):
                companies_list = [company.strip() if isinstance(company, str) else str(company).strip() for company in companies]
            else:
                return json.dumps({
                    "success": False,
                    "error": "Companies must be either a list of strings or a comma-separated string"
                }, indent=2)
            
            # Validate metric, quarter, year
            validation = self._validate_inputs(quarter=quarter, year=year, metric=metric)
            if not validation["valid"]:
                return json.dumps({
                    "success": False,
                    "error": "Validation failed",
                    "details": validation["errors"]
                }, indent=2)
            
            comparison_data = []
            missing_companies = []
            
            for company in companies_list:
                # Filter data for each company
                filtered_df = self.df[self.df['CompanyName'] == company].copy()
                
                if filtered_df.empty:
                    missing_companies.append(company)
                    continue
                
                # Add parsed quarter and year columns
                filtered_df['Quarter'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[0])
                filtered_df['Year'] = filtered_df['Datetime'].apply(lambda x: self._parse_quarter_year(x)[1])
                
                # Filter by quarter and year
                result_df = filtered_df[
                    (filtered_df['Quarter'] == quarter) & 
                    (filtered_df['Year'] == year)
                ]
                
                if not result_df.empty and metric in result_df.columns:
                    metric_value = result_df[metric].iloc[0]
                    comparison_data.append({
                        "company": company,
                        "value": float(metric_value) if pd.notna(metric_value) else None,
                        "date": result_df['Datetime'].iloc[0]
                    })
                else:
                    missing_companies.append(company)
            
            # Sort by metric value
            if comparison_data:
                comparison_data.sort(key=lambda x: x['value'] if x['value'] is not None else -float('inf'), 
                                   reverse=sort_descending)
            
            return json.dumps({
                "success": True,
                "data": {
                    "metric": metric,
                    "quarter": quarter,
                    "year": year,
                    "companies_found": len(comparison_data),
                    "companies_missing": missing_companies,
                    "sorted_descending": sort_descending,
                    "comparison": comparison_data
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error comparing companies: {str(e)}"
            }, indent=2)
    
    def get_available_companies(self) -> str:
        """
        Get list of all available companies in the dataset.
        
        Returns:
            JSON string with list of companies
        """
        try:
            companies = self.df['CompanyName'].unique().tolist()
            companies.sort()
            
            return json.dumps({
                "success": True,
                "data": {
                    "companies": companies,
                    "count": len(companies)
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error retrieving companies: {str(e)}"
            }, indent=2)
    
    def get_available_metrics(self) -> str:
        """
        Get list of all available financial metrics in the dataset.
        
        Returns:
            JSON string with list of metrics
        """
        try:
            # Get all columns except Datetime and CompanyName
            metrics = [col for col in self.df.columns if col not in ['Datetime', 'CompanyName']]
            metrics.sort()
            
            return json.dumps({
                "success": True,
                "data": {
                    "metrics": metrics,
                    "count": len(metrics)
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error retrieving metrics: {str(e)}"
            }, indent=2)

# Example usage
if __name__ == "__main__":
    # Initialize the tools (replace with actual Excel file path)
    # tools = FinancialDataTools("financial_data.xlsx")
    
    # Example function calls
    # result = tools.get_metric_for_company_quarter_year("JPMorgan Chase", "Revenue", 1, 2023)
    # print(result)
    
    # trend_result = tools.get_metric_trends("Bank of America", "EPS", 4)
    # print(trend_result)
    
    # comparison_result = tools.compare_companies_metric(
    #     ["JPMorgan Chase", "Bank of America", "Wells Fargo"], 
    #     "Revenue", 1, 2023
    # )
    # print(comparison_result)
    
    pass
