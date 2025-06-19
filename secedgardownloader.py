from secedgar.core.rest import get_company_facts
from datetime import datetime, timedelta
import pandas as pd

# ─── 1. CONFIGURE ────────────────────────────────────────────────────────────
USER_AGENT = "Your Name (your.email@example.com)"

TOP20 = [
    "JPM", "BAC", "WFC", "C", "USB", "PNC", "GS", "TFC", "COF",
    "BK",  "SCHW", "TCB", "AXP", "STT", "CFG", "FITB", "KEY", "RF", "NTRS", "HBAN"
]

# threshold for “last decade”
cutoff_date = datetime.now() - timedelta(days=365 * 10)


# ─── 2. FETCH & FLATTEN ALL FACTS ────────────────────────────────────────────
records = []
for ticker in TOP20:
    # fetch every fact for this ticker
    facts_dict = get_company_facts(lookups=ticker, user_agent=USER_AGENT)
    resp = facts_dict.get(ticker)
    if resp is None:
        continue
    usgaap = resp.get("facts", {}).get("us-gaap", {})
    
    for tag, info in usgaap.items():
        for unit, entries in info.get("units", {}).items():
            if unit != "USD":
                continue
            
            for entry in entries:
                form = entry.get("form")
                if form not in ("10-K", "10-Q"):
                    continue
                
                period_end = datetime.fromisoformat(entry.get("end"))
                if period_end < cutoff_date:
                    continue

                records.append({
                    "Company": ticker,
                    "Datetime": period_end,
                    "Metric": tag,
                    "Value": entry.get("val")
                })


# ─── 3. BUILD WIDE DATAFRAME ─────────────────────────────────────────────────
# build dataframe and pivot to wide format
df = pd.DataFrame.from_records(records)

df_wide = (
    df
    .pivot_table(
        index=["Company", "Datetime"],
        columns="Metric",
        values="Value",
        aggfunc="first"
    )
    .reset_index()
)
# remove axis name and sort
df_wide.columns.name = None
df_wide = df_wide.sort_values(["Company", "Datetime"])

# ─── 4. SAVE TO EXCEL ────────────────────────────────────────────────────────
output_path = "top20_banks_last10yrs.xlsx"
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    df_wide.to_excel(writer, index=False, sheet_name="Earnings")  

print(f"✔️ Saved earnings metrics to {output_path}")
