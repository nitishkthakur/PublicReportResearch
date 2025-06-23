import os
import re
import time
import pdfkit
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ── Configuration ───────────────────────────────────────────────

BANK_CIK_MAP = {
    'JPMorgan_Chase':       '0000019617',
    'Bank_of_America':      '0000070858',
    'Wells_Fargo':          '0000072971',
    'Citigroup':            '0000831001',
    'US_Bancorp':           '0000036104',
    'PNC':                  '0000713676',
    'Goldman_Sachs':        '0000886982',
    'Truist':               '0000092230',
    'Capital_One':          '0000927628',
    'BNY_Mellon':           '0001390777',
    'Charles_Schwab':       '0000316709',
    'TD_Group':             '0001843204',
    'American_Express':     '0000004962',
    'State_Street':         '0000093751',
    'Citizens_Financial':   '0001378946',
    'Fifth_Third':          '0000035527',
    'KeyCorp':              '0000091576',
    'Regions_Financial':    '0000039899',
    'Northern_Trust':       '0000073124',
    'Huntington_Bancshares': '0000049196',
}

START_DATE = datetime.now() - timedelta(days=365*10)
API_URL    = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_BASE = "https://www.sec.gov"
OUTPUT_DIR = "MD&A_PDFs"
HEADERS    = {
    'User-Agent': 'Your Name your_email@example.com',
    'Accept-Encoding': 'gzip, deflate',
}

# ── Helpers ────────────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def quarter_from_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"Q{((dt.month-1)//3)+1}{dt.year}"

def fetch_filings(cik):
    """Return list of (date, accession, document) for 10-Q filings."""
    url = API_URL.format(cik=cik.zfill(10))
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json().get('filings', {}).get('recent', {})
    filings = []
    for form, date, acc, doc in zip(
        data.get('form', []),
        data.get('filingDate', []),
        data.get('accessionNumber', []),
        data.get('primaryDocument', [])
    ):
        if form == '10-Q' and date >= START_DATE.strftime("%Y-%m-%d"):
            filings.append((date, acc.replace('-', ''), doc))
    return filings

def extract_mda(html):
    """Return HTML snippet for Item 2 MD&A section."""
    # Regex from "Item 2." up to next "Item 3"
    match = re.search(
        r"(Item\s+2\.[\s\S]*?)(?=Item\s+3\.)",
        html, re.IGNORECASE
    )
    return match.group(1) if match else None

# ── Main Workflow ─────────────────────────────────────────────

def main():
    ensure_dir(OUTPUT_DIR)
    session = requests.Session()
    session.headers.update(HEADERS)

    for bank, cik in BANK_CIK_MAP.items():
        bank_dir = os.path.join(OUTPUT_DIR, bank)
        ensure_dir(bank_dir)

        for date, acc, doc in fetch_filings(cik):
            # Fetch the filing HTML
            url = f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
            resp = session.get(url)
            resp.raise_for_status()

            # Extract MD&A section
            mda_html = extract_mda(resp.text)
            if not mda_html:
                continue

            # Convert to PDF
            fname = f"{bank}_management_{quarter_from_date(date)}.pdf"
            out_path = os.path.join(bank_dir, fname)
            pdfkit.from_string(mda_html, out_path)

            time.sleep(0.2)

if __name__ == "__main__":
    main()