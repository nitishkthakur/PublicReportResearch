import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SECBankDataExtractor:
    def __init__(self, user_agent: str = "YourCompany yourname@yourcompany.com"):
        """
        Initialize the SEC data extractor
        
        Args:
            user_agent: Required user agent for SEC API requests
        """
        self.user_agent = user_agent
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        
        # Top 20 US Banks by Assets (CIK numbers)
        self.top_banks = {
            'JPMorgan Chase & Co.': '0000019617',
            'Bank of America Corp': '0000070858',
            'Wells Fargo & Company': '0000072971',
            'Citigroup Inc.': '0000831001',
            'U.S. Bancorp': '0000036104',
            'PNC Financial Services Group Inc': '0000713676',
            'Goldman Sachs Group Inc': '0000886982',
            'Truist Financial Corporation': '0000092230',
            'Capital One Financial Corp': '0000927628',
            'Bank of New York Mellon Corp': '0001390777',
            'Charles Schwab Corporation': '0000316709',
            'TD Group US Holdings LLC': '0001843204',
            'American Express Company': '0000004962',
            'State Street Corporation': '0000093751',
            'Citizens Financial Group Inc': '0001378946',
            'Fifth Third Bancorp': '0000035527',
            'KeyCorp': '0000091576',
            'Regions Financial Corporation': '0000039899',
            'Northern Trust Corporation': '0000073124',
            'Huntington Bancshares Inc': '0000049196'
        }
        
        # Key financial metrics to extract
        self.target_metrics = [
            'TotalRevenue',
            'InterestIncome',
            'NonInterestIncome',
            'InterestExpense',
            'NetInterestIncome',
            'ProvisionForLoanLosses',
            'NonInterestExpense',
            'NetIncome',
            'EarningsPerShare',
            'TotalAssets',
            'TotalLoans',
            'TotalDeposits',
            'ShareholdersEquity',
            'BookValuePerShare',
            'ReturnOnAssets',
            'ReturnOnEquity'
        ]
    
    def get_company_facts(self, cik: str) -> Optional[Dict]:
        """
        Get company facts from SEC API
        
        Args:
            cik: Company CIK number
            
        Returns:
            Dictionary containing company facts or None if error
        """
        try:
            url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get company facts for CIK {cik}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting company facts for CIK {cik}: {str(e)}")
            return None
    
    def get_company_filings(self, cik: str, start_date: str, end_date: str) -> Optional[Dict]:
        """
        Get company filings from SEC API
        
        Args:
            cik: Company CIK number
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing filings data or None if error
        """
        try:
            url = f"{self.base_url}/api/xbrl/submissions/CIK{cik.zfill(10)}.json"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                # Filter filings by date and form type
                filings = []
                recent_filings = data.get('filings', {}).get('recent', {})
                
                if recent_filings:
                    for i in range(len(recent_filings.get('form', []))):
                        form_type = recent_filings['form'][i]
                        filing_date = recent_filings['filingDate'][i]
                        
                        if form_type in ['10-K', '10-Q'] and start_date <= filing_date <= end_date:
                            filings.append({
                                'form': form_type,
                                'filingDate': filing_date,
                                'accessionNumber': recent_filings['accessionNumber'][i],
                                'reportDate': recent_filings.get('reportDate', [''])[i],
                                'primaryDocument': recent_filings.get('primaryDocument', [''])[i]
                            })
                
                return {'filings': filings}
            else:
                logger.warning(f"Failed to get filings for CIK {cik}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting filings for CIK {cik}: {str(e)}")
            return None
    
    def extract_financial_metrics(self, company_facts: Dict, start_date: str, end_date: str) -> List[Dict]:
        """
        Extract financial metrics from company facts
        
        Args:
            company_facts: Company facts data from SEC API
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of dictionaries containing extracted metrics
        """
        metrics_data = []
        
        try:
            facts = company_facts.get('facts', {})
            us_gaap = facts.get('us-gaap', {})
            dei = facts.get('dei', {})
            
            # Common GAAP tags mapping to our target metrics
            gaap_mapping = {
                'TotalRevenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'InterestAndDividendIncomeOperating'],
                'InterestIncome': ['InterestAndFeeIncomeLoansAndLeases', 'InterestIncomeOperating', 'InterestAndDividendIncomeOperating'],
                'NonInterestIncome': ['NoninterestIncome', 'RevenuesExcludingInterestAndDividends'],
                'InterestExpense': ['InterestExpense', 'InterestExpenseDeposits', 'InterestExpenseDebt'],
                'NetInterestIncome': ['InterestIncomeExpenseNet', 'NetInterestIncome'],
                'ProvisionForLoanLosses': ['ProvisionForLoanAndLeaseLosses', 'ProvisionForCreditLosses'],
                'NonInterestExpense': ['NoninterestExpense', 'OperatingExpenses'],
                'NetIncome': ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic'],
                'EarningsPerShare': ['EarningsPerShareBasic', 'EarningsPerShareDiluted'],
                'TotalAssets': ['Assets', 'AssetsCurrent'],
                'TotalLoans': ['LoansAndLeasesReceivableNetOfAllowance', 'LoansAndLeasesReceivableGross'],
                'TotalDeposits': ['Deposits', 'DepositsTotal'],
                'ShareholdersEquity': ['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']
            }
            
            # Get all available periods
            all_periods = set()
            for metric_group in gaap_mapping.values():
                for tag in metric_group:
                    if tag in us_gaap:
                        for unit_type in us_gaap[tag].get('units', {}):
                            for entry in us_gaap[tag]['units'][unit_type]:
                                if 'end' in entry and start_date <= entry['end'] <= end_date:
                                    all_periods.add(entry['end'])
            
            # Extract data for each period
            for period_end in sorted(all_periods):
                period_data = {
                    'Datetime': period_end,
                    'CompanyName': company_facts.get('entityName', 'Unknown')
                }
                
                # Extract each metric
                for target_metric, possible_tags in gaap_mapping.items():
                    value = None
                    for tag in possible_tags:
                        if tag in us_gaap:
                            for unit_type in us_gaap[tag].get('units', {}):
                                for entry in us_gaap[tag]['units'][unit_type]:
                                    if entry.get('end') == period_end and 'val' in entry:
                                        # Prefer quarterly data (form 10-Q) over annual
                                        if entry.get('form') in ['10-Q', '10-K']:
                                            value = entry['val']
                                            break
                                if value is not None:
                                    break
                        if value is not None:
                            break
                    
                    period_data[target_metric] = value
                
                # Only add if we have some meaningful data
                if any(period_data[metric] is not None for metric in self.target_metrics):
                    metrics_data.append(period_data)
        
        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
        
        return metrics_data
    
    def download_bank_data(self, start_date: str = "2019-01-01", end_date: str = "2025-12-31") -> pd.DataFrame:
        """
        Download earnings data for all banks
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame containing all bank earnings data
        """
        all_data = []
        
        logger.info(f"Starting data download for {len(self.top_banks)} banks from {start_date} to {end_date}")
        
        for i, (bank_name, cik) in enumerate(self.top_banks.items()):
            logger.info(f"Processing {i+1}/{len(self.top_banks)}: {bank_name}")
            
            try:
                # Get company facts
                company_facts = self.get_company_facts(cik)
                if company_facts:
                    # Extract metrics
                    bank_metrics = self.extract_financial_metrics(company_facts, start_date, end_date)
                    all_data.extend(bank_metrics)
                    
                    logger.info(f"Extracted {len(bank_metrics)} records for {bank_name}")
                else:
                    logger.warning(f"No company facts found for {bank_name}")
                
                # Rate limiting - SEC allows 10 requests per second
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing {bank_name}: {str(e)}")
                continue
        
        # Create DataFrame
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            # Convert datetime column
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            
            # Sort by company and date
            df = df.sort_values(['CompanyName', 'Datetime'])
            
            # Reset index
            df = df.reset_index(drop=True)
            
            logger.info(f"Successfully extracted {len(df)} total records")
        else:
            logger.warning("No data was extracted")
        
        return df
    
    def save_to_excel(self, df: pd.DataFrame, filename: str = "bank_earnings_data.xlsx"):
        """
        Save DataFrame to Excel file
        
        Args:
            df: DataFrame to save
            filename: Output filename
        """
        try:
            # Create Excel writer
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Bank_Earnings_Data', index=False)
                
                # Summary sheet
                if not df.empty:
                    summary_data = []
                    for company in df['CompanyName'].unique():
                        company_data = df[df['CompanyName'] == company]
                        summary_data.append({
                            'Company': company,
                            'Records': len(company_data),
                            'Date_Range': f"{company_data['Datetime'].min().strftime('%Y-%m-%d')} to {company_data['Datetime'].max().strftime('%Y-%m-%d')}",
                            'Latest_Revenue': company_data['TotalRevenue'].dropna().iloc[-1] if not company_data['TotalRevenue'].dropna().empty else None,
                            'Latest_Net_Income': company_data['NetIncome'].dropna().iloc[-1] if not company_data['NetIncome'].dropna().empty else None
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            logger.info(f"Data saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving to Excel: {str(e)}")

def main():
    """
    Main function to run the SEC bank data extraction
    """
    # Initialize extractor
    # IMPORTANT: Replace with your actual contact information
    extractor = SECBankDataExtractor(user_agent="YourCompany yourname@yourcompany.com")
    
    # Set date range (default 2019-2025)
    start_date = "2019-01-01"
    end_date = "2025-12-31"
    
    print(f"SEC Bank Earnings Data Extractor")
    print(f"================================")
    print(f"Downloading data from {start_date} to {end_date}")
    print(f"Target banks: {len(extractor.top_banks)}")
    print(f"Target metrics: {len(extractor.target_metrics)}")
    print()
    
    # Download data
    df = extractor.download_bank_data(start_date, end_date)
    
    if not df.empty:
        print(f"\nData extraction completed!")
        print(f"Total records: {len(df)}")
        print(f"Companies with data: {df['CompanyName'].nunique()}")
        print(f"Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")
        
        # Save to Excel
        output_filename = f"bank_earnings_data_{start_date}_{end_date}.xlsx"
        extractor.save_to_excel(df, output_filename)
        
        print(f"\nData saved to: {output_filename}")
        
        # Display sample data
        print(f"\nSample data preview:")
        print(df.head())
        
    else:
        print("No data was extracted. Please check the logs for errors.")

if __name__ == "__main__":
    main()