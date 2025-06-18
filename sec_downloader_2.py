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
        
        # Top 50 financial metrics prioritized by importance for banking stakeholders
        # Order: Most critical metrics first (profitability, capital, risk) -> operational -> growth -> regulatory
        self.target_metrics = [
            # TIER 1: Core Profitability & Performance (Most Important)
            'NetIncome',                           # Bottom line profitability
            'TotalRevenue',                        # Top line revenue
            'NetInterestIncome',                   # Core banking income
            'ReturnOnEquity',                      # Key profitability ratio
            'ReturnOnAssets',                      # Asset efficiency
            'EarningsPerShare',                    # Shareholder value
            'EarningsPerShareDiluted',             # Diluted EPS
            
            # TIER 2: Capital & Balance Sheet Strength
            'TotalAssets',                         # Bank size/scale
            'ShareholdersEquity',                  # Capital base
            'TotalDeposits',                       # Funding base
            'TotalLoans',                          # Core asset
            'BookValuePerShare',                   # Per-share equity value
            'TangibleBookValuePerShare',           # Tangible equity value
            'Tier1CapitalRatio',                   # Regulatory capital
            
            # TIER 3: Risk Management & Credit Quality
            'ProvisionForLoanLosses',              # Credit risk expense
            'AllowanceForLoanLosses',              # Credit loss reserves
            'NonPerformingLoans',                  # Problem assets
            'ChargeOffs',                          # Realized losses
            'LoanLossReserveRatio',                # Reserve coverage
            'NonPerformingAssetRatio',             # Asset quality
            
            # TIER 4: Income Statement Detail
            'InterestIncome',                      # Interest revenue
            'InterestExpense',                     # Interest costs
            'NonInterestIncome',                   # Fee income
            'NonInterestExpense',                  # Operating expenses
            'OperatingExpenses',                   # Total opex
            'PersonnelExpense',                    # Staff costs
            'OccupancyExpense',                    # Facility costs
            
            # TIER 5: Operational Efficiency
            'EfficiencyRatio',                     # Cost efficiency
            'NetInterestMargin',                   # Spread profitability
            'CostOfFunds',                         # Funding cost
            'AssetTurnover',                       # Asset utilization
            'OperatingLeverage',                   # Operating efficiency
            
            # TIER 6: Growth & Market Metrics
            'TotalRevenueGrowth',                  # Revenue growth
            'LoanGrowth',                          # Loan portfolio growth
            'DepositGrowth',                       # Deposit growth
            'TangibleEquityRatio',                 # Tangible capital ratio
            'LeverageRatio',                       # Financial leverage
            
            # TIER 7: Trading & Investment Banking
            'TradingRevenue',                      # Trading income
            'InvestmentBankingRevenue',            # IB fees
            'TrustAndInvestmentFees',              # Wealth management
            'ServiceCharges',                      # Service fees
            'CardRevenue',                         # Credit card income
            
            # TIER 8: Regulatory & Capital Management
            'CommonEquityTier1Ratio',              # CET1 ratio
            'TotalCapitalRatio',                   # Total capital
            'RiskWeightedAssets',                  # RWA
            'LeverageCapitalRatio',                # Leverage ratio
            'LiquidityRatio',                      # Liquidity position
            
            # TIER 9: Additional Balance Sheet Items
            'TradingAssets',                       # Trading portfolio
            'AvailableForSaleSecurities',          # AFS securities
            'HeldToMaturitySecurities',            # HTM securities
            'Goodwill',                            # Goodwill asset
            'IntangibleAssets'                     # Other intangibles
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
            
            # Comprehensive GAAP tags mapping to our 50 target metrics
            gaap_mapping = {
                # TIER 1: Core Profitability & Performance
                'NetIncome': ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic', 'IncomeLossFromContinuingOperations'],
                'TotalRevenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'InterestAndDividendIncomeOperating', 'TotalRevenues'],
                'NetInterestIncome': ['InterestIncomeExpenseNet', 'NetInterestIncome', 'InterestIncomeExpenseAfterProvisionForLoanLoss'],
                'ReturnOnEquity': ['ReturnOnAverageEquity', 'ReturnOnEquity'],
                'ReturnOnAssets': ['ReturnOnAverageAssets', 'ReturnOnAssets'],
                'EarningsPerShare': ['EarningsPerShareBasic', 'IncomeLossFromContinuingOperationsPerBasicShare'],
                'EarningsPerShareDiluted': ['EarningsPerShareDiluted', 'IncomeLossFromContinuingOperationsPerDilutedShare'],
                
                # TIER 2: Capital & Balance Sheet Strength
                'TotalAssets': ['Assets', 'AssetsCurrent', 'AssetsNoncurrent'],
                'ShareholdersEquity': ['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'EquityAttributableToParent'],
                'TotalDeposits': ['Deposits', 'DepositsTotal', 'InterestBearingDeposits', 'NoninterestBearingDeposits'],
                'TotalLoans': ['LoansAndLeasesReceivableNetOfAllowance', 'LoansAndLeasesReceivableGross', 'LoansReceivableNet'],
                'BookValuePerShare': ['BookValuePerShare', 'StockholdersEquityPerShare'],
                'TangibleBookValuePerShare': ['TangibleBookValuePerShare'],
                'Tier1CapitalRatio': ['Tier1CapitalRatio', 'CapitalAdequacyTier1CapitalRatio'],
                
                # TIER 3: Risk Management & Credit Quality
                'ProvisionForLoanLosses': ['ProvisionForLoanAndLeaseLosses', 'ProvisionForCreditLosses', 'ProvisionForDoubtfulAccounts'],
                'AllowanceForLoanLosses': ['AllowanceForLoanAndLeaseLosses', 'AllowanceForCreditLossesFinancingReceivables'],
                'NonPerformingLoans': ['LoansAndLeasesReceivableNonaccrual', 'NonperformingLoans'],
                'ChargeOffs': ['LoansAndLeasesReceivableChargeOffs', 'ChargeOffsLoansAndLeases'],
                'LoanLossReserveRatio': ['LoanLossReserveRatio'],
                'NonPerformingAssetRatio': ['NonperformingAssetRatio'],
                
                # TIER 4: Income Statement Detail
                'InterestIncome': ['InterestAndFeeIncomeLoansAndLeases', 'InterestIncomeOperating', 'InterestAndDividendIncomeOperating', 'InterestIncomeLoansAndLeases'],
                'InterestExpense': ['InterestExpense', 'InterestExpenseDeposits', 'InterestExpenseDebt', 'InterestExpenseBorrowings'],
                'NonInterestIncome': ['NoninterestIncome', 'RevenuesExcludingInterestAndDividends', 'FeesAndCommissions'],
                'NonInterestExpense': ['NoninterestExpense', 'OperatingExpenses', 'GeneralAndAdministrativeExpense'],
                'OperatingExpenses': ['OperatingExpenses', 'CostsAndExpenses', 'OperatingCostsAndExpenses'],
                'PersonnelExpense': ['LaborAndRelatedExpense', 'EmployeeRelatedExpense', 'SalariesAndWages'],
                'OccupancyExpense': ['OccupancyNet', 'OccupancyAndEquipmentExpense'],
                
                # TIER 5: Operational Efficiency
                'EfficiencyRatio': ['EfficiencyRatio'],
                'NetInterestMargin': ['NetInterestMargin'],
                'CostOfFunds': ['CostOfFunds'],
                'AssetTurnover': ['AssetTurnover'],
                'OperatingLeverage': ['OperatingLeverage'],
                
                # TIER 6: Growth & Market Metrics
                'TotalRevenueGrowth': ['RevenueGrowthRate'],
                'LoanGrowth': ['LoanGrowthRate'],
                'DepositGrowth': ['DepositGrowthRate'],
                'TangibleEquityRatio': ['TangibleEquityRatio'],
                'LeverageRatio': ['LeverageRatio', 'DebtToEquityRatio'],
                
                # TIER 7: Trading & Investment Banking
                'TradingRevenue': ['TradingGainsLosses', 'TradingAccountProfitLoss', 'SecuritiesGainLoss'],
                'InvestmentBankingRevenue': ['InvestmentBankingRevenue', 'UnderwritingIncome'],
                'TrustAndInvestmentFees': ['TrustFeesRevenue', 'InvestmentManagementAndTrustFees'],
                'ServiceCharges': ['ServiceChargesOnDepositAccounts', 'ServiceCharges'],
                'CardRevenue': ['CreditCardIncome', 'CreditCardFees'],
                
                # TIER 8: Regulatory & Capital Management
                'CommonEquityTier1Ratio': ['CommonEquityTier1CapitalRatio', 'Tier1CommonCapitalRatio'],
                'TotalCapitalRatio': ['TotalCapitalRatio', 'CapitalAdequacyTotalCapitalRatio'],
                'RiskWeightedAssets': ['RiskWeightedAssets'],
                'LeverageCapitalRatio': ['LeverageRatio', 'CapitalAdequacyLeverageRatio'],
                'LiquidityRatio': ['LiquidityRatio', 'LiquidityCoverageRatio'],
                
                # TIER 9: Additional Balance Sheet Items
                'TradingAssets': ['TradingSecuritiesDebt', 'TradingSecuritiesEquity', 'TradingSecurities'],
                'AvailableForSaleSecurities': ['AvailableForSaleSecuritiesDebtSecurities', 'MarketableSecuritiesAvailableForSale'],
                'HeldToMaturitySecurities': ['HeldToMaturitySecurities', 'DebtSecuritiesHeldToMaturity'],
                'Goodwill': ['Goodwill'],
                'IntangibleAssets': ['IntangibleAssetsNetExcludingGoodwill', 'FiniteLivedIntangibleAssetsNet']
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
                                        # Prefer quarterly data (form 10-Q) over annual, and recent over old
                                        if entry.get('form') in ['10-Q', '10-K']:
                                            if value is None or entry.get('form') == '10-Q':
                                                value = entry['val']
                                            break
                                if value is not None:
                                    break
                        if value is not None:
                            break
                    
                    period_data[target_metric] = value
                
                # Only add if we have some meaningful data (at least core metrics)
                core_metrics = ['NetIncome', 'TotalRevenue', 'TotalAssets', 'ShareholdersEquity']
                if any(period_data.get(metric) is not None for metric in core_metrics):
                    metrics_data.append(period_data)
        
        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
        
        return metrics_data
    
    def calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate derived financial metrics that can't be directly extracted
        
        Args:
            df: DataFrame with base financial metrics
            
        Returns:
            DataFrame with additional calculated metrics
        """
        try:
            # Calculate ROE if not available (Net Income / Shareholders Equity)
            mask = (df['ReturnOnEquity'].isna()) & (df['NetIncome'].notna()) & (df['ShareholdersEquity'].notna()) & (df['ShareholdersEquity'] != 0)
            df.loc[mask, 'ReturnOnEquity'] = (df.loc[mask, 'NetIncome'] / df.loc[mask, 'ShareholdersEquity']) * 100
            
            # Calculate ROA if not available (Net Income / Total Assets)
            mask = (df['ReturnOnAssets'].isna()) & (df['NetIncome'].notna()) & (df['TotalAssets'].notna()) & (df['TotalAssets'] != 0)
            df.loc[mask, 'ReturnOnAssets'] = (df.loc[mask, 'NetIncome'] / df.loc[mask, 'TotalAssets']) * 100
            
            # Calculate Book Value Per Share if not available
            mask = (df['BookValuePerShare'].isna()) & (df['ShareholdersEquity'].notna())
            # Note: Would need shares outstanding data which may not be readily available
            
            # Calculate Efficiency Ratio if not available (Non-Interest Expense / (Net Interest Income + Non-Interest Income))
            mask = (df['EfficiencyRatio'].isna()) & (df['NonInterestExpense'].notna()) & \
                   ((df['NetInterestIncome'].notna()) | (df['NonInterestIncome'].notna()))
            
            revenue_base = df['NetInterestIncome'].fillna(0) + df['NonInterestIncome'].fillna(0)
            df.loc[mask & (revenue_base != 0), 'EfficiencyRatio'] = (df.loc[mask & (revenue_base != 0), 'NonInterestExpense'] / revenue_base.loc[mask & (revenue_base != 0)]) * 100
            
            # Calculate Net Interest Margin if not available
            # This would require average earning assets data which may not be available
            
            logger.info("Calculated derived financial metrics")
            
        except Exception as e:
            logger.error(f"Error calculating derived metrics: {str(e)}")
        
        return df
    
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
        logger.info(f"Extracting {len(self.target_metrics)} financial metrics")
        
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
            
            # Ensure all target metrics are present as columns (even if empty)
            for metric in self.target_metrics:
                if metric not in df.columns:
                    df[metric] = None
            
            # Reorder columns: Datetime, CompanyName, then metrics in priority order
            column_order = ['Datetime', 'CompanyName'] + self.target_metrics
            df = df.reindex(columns=column_order)
            
            # Calculate derived metrics
            df = self.calculate_derived_metrics(df)
            
            # Sort by company and date
            df = df.sort_values(['CompanyName', 'Datetime'])
            
            # Reset index
            df = df.reset_index(drop=True)
            
            logger.info(f"Successfully extracted {len(df)} total records with {len(self.target_metrics)} metrics")
        else:
            logger.warning("No data was extracted")
        
        return df
    
    def save_to_excel(self, df: pd.DataFrame, filename: str = "bank_earnings_data.xlsx"):
        """
        Save DataFrame to Excel file with enhanced formatting
        
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
                        latest_data = company_data.iloc[-1] if len(company_data) > 0 else None
                        
                        summary_data.append({
                            'Company': company,
                            'Records': len(company_data),
                            'Date_Range': f"{company_data['Datetime'].min().strftime('%Y-%m-%d')} to {company_data['Datetime'].max().strftime('%Y-%m-%d')}",
                            'Latest_Total_Assets': latest_data['TotalAssets'] if latest_data is not None else None,
                            'Latest_Net_Income': latest_data['NetIncome'] if latest_data is not None else None,
                            'Latest_ROE': latest_data['ReturnOnEquity'] if latest_data is not None else None,
                            'Latest_ROA': latest_data['ReturnOnAssets'] if latest_data is not None else None,
                            'Data_Quality_Score': f"{(company_data[self.target_metrics].notna().sum().sum() / (len(company_data) * len(self.target_metrics)) * 100):.1f}%"
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Metrics Dictionary sheet
                metrics_info = []
                tier_descriptions = {
                    'TIER 1': 'Core Profitability & Performance - Most critical metrics for stakeholder decision making',
                    'TIER 2': 'Capital & Balance Sheet Strength - Financial stability and scale indicators',
                    'TIER 3': 'Risk Management & Credit Quality - Credit risk and asset quality measures',
                    'TIER 4': 'Income Statement Detail - Detailed revenue and expense components',
                    'TIER 5': 'Operational Efficiency - Cost management and operational performance',
                    'TIER 6': 'Growth & Market Metrics - Growth rates and market position indicators',
                    'TIER 7': 'Trading & Investment Banking - Specialized revenue streams',
                    'TIER 8': 'Regulatory & Capital Management - Regulatory compliance metrics',
                    'TIER 9': 'Additional Balance Sheet Items - Supporting balance sheet components'
                }
                
                current_tier = None
                tier_counters = {'TIER 1': 0, 'TIER 2': 0, 'TIER 3': 0, 'TIER 4': 0, 'TIER 5': 0, 
                               'TIER 6': 0, 'TIER 7': 0, 'TIER 8': 0, 'TIER 9': 0}
                
                for i, metric in enumerate(self.target_metrics):
                    # Determine tier based on position
                    if i < 7: tier = 'TIER 1'
                    elif i < 15: tier = 'TIER 2'
                    elif i < 21: tier = 'TIER 3'
                    elif i < 28: tier = 'TIER 4'
                    elif i < 33: tier = 'TIER 5'
                    elif i < 38: tier = 'TIER 6'
                    elif i < 43: tier = 'TIER 7'
                    elif i < 48: tier = 'TIER 8'
                    else: tier = 'TIER 9'
                    
                    tier_counters[tier] += 1
                    
                    metrics_info.append({
                        'Metric_Name': metric,
                        'Priority_Rank': i + 1,
                        'Tier': tier,
                        'Tier_Description': tier_descriptions[tier],
                        'Column_Position': i + 3  # +3 for Datetime and CompanyName columns
                    })
                
                metrics_df = pd.DataFrame(metrics_info)
                metrics_df.to_excel(writer, sheet_name='Metrics_Dictionary', index=False)
            
            logger.info(f"Data saved to {filename}")
            logger.info(f"Excel file contains 3 sheets: Bank_Earnings_Data, Summary, and Metrics_Dictionary")
            
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
    
    print(f"SEC Bank Earnings Data Extractor - Enhanced Version")
    print(f"==================================================")
    print(f"Downloading data from {start_date} to {end_date}")
    print(f"Target banks: {len(extractor.top_banks)}")
    print(f"Target metrics: {len(extractor.target_metrics)} (prioritized by stakeholder importance)")
    print()
    
    # Display metric tiers
    print("Metric Priority Tiers:")
    print("TIER 1 (1-7): Core Profitability & Performance")
    print("TIER 2 (8-15): Capital & Balance Sheet Strength") 
    print("TIER 3 (16-21): Risk Management & Credit Quality")
    print("TIER 4 (22-28): Income Statement Detail")
    print("TIER 5 (29-33): Operational Efficiency")
    print("TIER 6 (34-38): Growth & Market Metrics")
    print("TIER 7 (39-43): Trading & Investment Banking")
    print("TIER 8 (44-48): Regulatory & Capital Management")
    print("TIER 9 (49-50): Additional Balance Sheet Items")
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
        
        # Display data quality metrics
        total_possible_values = len(df) * len(extractor.target_metrics)
        actual_values = df[extractor.target_metrics].notna().sum().sum()
        data_completeness = (actual_values / total_possible_values) * 100
        
        print(f"\nData Quality Summary:")
        print(f"Data completeness: {data_completeness:.1f}%")
        print(f"Total possible data points: {total_possible_values:,}")
        print(f"Actual data points extracted: {actual_values:,}")
        
        # Show top metrics by data availability
        print(f"\nTop 10 metrics by data availability:")
        metric_availability = df[extractor.target_metrics].notna().sum().sort_values(ascending=False)
        for i, (metric, count) in enumerate(metric_availability.head(10).items()):
            percentage = (count / len(df)) * 100
            print(f"{i+1:2d}. {metric:<25} {count:4d} records ({percentage:5.1f}%)")
        
        # Display sample data for most important metrics
        important_columns = ['Datetime', 'CompanyName'] + extractor.target_metrics[:10]
        print(f"\nSample data preview (Top 10 priority metrics):")
        print(df[important_columns].head(3).to_string(index=False))
        
        # Show metrics by tier
        print(f"\nMetrics organized by priority tiers:")
        tier_ranges = [
            (1, 7, "TIER 1: Core Profitability & Performance"),
            (8, 15, "TIER 2: Capital & Balance Sheet Strength"),
            (16, 21, "TIER 3: Risk Management & Credit Quality"),
            (22, 28, "TIER 4: Income Statement Detail"),
            (29, 33, "TIER 5: Operational Efficiency"),
            (34, 38, "TIER 6: Growth & Market Metrics"),
            (39, 43, "TIER 7: Trading & Investment Banking"),
            (44, 48, "TIER 8: Regulatory & Capital Management"),
            (49, 50, "TIER 9: Additional Balance Sheet Items")
        ]
        
        for start_idx, end_idx, tier_name in tier_ranges:
            print(f"\n{tier_name}:")
            tier_metrics = extractor.target_metrics[start_idx-1:end_idx]
            for i, metric in enumerate(tier_metrics, start_idx):
                availability = df[metric].notna().sum()
                percentage = (availability / len(df)) * 100 if len(df) > 0 else 0
                print(f"  {i:2d}. {metric:<30} ({availability:3d} records, {percentage:5.1f}%)")
        
    else:
        print("No data was extracted. Please check the logs for errors.")
        print("\nTroubleshooting suggestions:")
        print("1. Verify your User-Agent contains valid company name and email")
        print("2. Check your internet connection")
        print("3. Ensure the date range contains valid reporting periods")
        print("4. Review the logs above for specific error messages")

if __name__ == "__main__":
    main()