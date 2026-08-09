from io import BytesIO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np

app = FastAPI()

def sanitize_val(val, default=0.0):
    if pd.isna(val) or np.isinf(val):
        return default
    return float(val)

@app.post("/api/analyze-fao-cpi")
async def analyze_fao_cpi(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        raw_df = pd.read_csv(BytesIO(contents))

        # 1. Flexible Column Mapping (Normalize column names)
        col_map = {col.lower().strip(): col for col in raw_df.columns}
        
        item_col = col_map.get("item", None)
        year_col = col_map.get("year", None)
        val_col = col_map.get("value", None)
        
        if not year_col or not val_col:
            return JSONResponse(
                status_code=400, 
                content={"error": f"CSV missing required columns ('Year', 'Value'). Found: {list(raw_df.columns)}"}
            )

        # 2. Extract Items/Categories
        items = raw_df[item_col].dropna().unique().tolist() if item_col else []

        if "Food Indices" in items:
            df = raw_df[raw_df[item_col] == "Food Indices"].copy()
        elif items:
            df = raw_df[raw_df[item_col] == items[0]].copy()
        else:
            df = raw_df.copy()

        # 3. Clean Numeric Values
        df["Year"] = pd.to_numeric(df[year_col], errors="coerce")
        df["Value"] = pd.to_numeric(df[val_col], errors="coerce")

        # 4. Smart Month Resolution
        if "months code" in col_map:
            # FAOSTAT Codes (e.g., 7001=Jan, 7012=Dec)
            m_code = pd.to_numeric(df[col_map["months code"]], errors="coerce")
            df["Month"] = m_code.apply(
                lambda x: x - 7000 if 7001 <= x <= 7012 else (x if 1 <= x <= 12 else np.nan)
            )
        elif "months" in col_map:
            # Full month names ("January") or abbreviations ("Jan")
            months_series = df[col_map["months"]].astype(str).str.strip()
            df["Month"] = pd.to_datetime(months_series, format="%B", errors="coerce").dt.month
            
            # Fallback to short month names if %B fails
            if df["Month"].isna().all():
                df["Month"] = pd.to_datetime(months_series, format="%b", errors="coerce").dt.month
            # Fallback to direct numbers
            if df["Month"].isna().all():
                df["Month"] = pd.to_numeric(months_series, errors="coerce")
        elif "month" in col_map:
            df["Month"] = pd.to_numeric(df[col_map["month"]], errors="coerce")
        else:
            # Fallback if annual dataset without months
            df["Month"] = 1

        # 5. Drop Invalid Rows and Sort Chronologically
        df = df.dropna(subset=["Year", "Month", "Value"])
        df = df[(df["Month"] >= 1) & (df["Month"] <= 12)]
        df = df.sort_values(by=["Year", "Month"]).reset_index(drop=True)

        if df.empty:
            return JSONResponse(
                status_code=400, 
                content={"error": "No valid monthly records found in the uploaded file."}
            )

        # 6. Build Datetime Column
        df["Date"] = pd.to_datetime(
            df["Year"].astype(int).astype(str) + "-" + df["Month"].astype(int).astype(str) + "-01",
            errors="coerce"
        )
        df = df.dropna(subset=["Date"])

        # 7. Calculate Month-over-Month Growth Rate %
        df["MoM_Growth"] = (df["Value"].pct_change() * 100).fillna(0.0).round(2)

        # 8. Statistical Summary
        min_val = sanitize_val(df["Value"].min())
        max_val = sanitize_val(df["Value"].max())
        avg_val = sanitize_val(df["Value"].mean())
        avg_growth = sanitize_val(df["MoM_Growth"].mean())

        # Peak Inflation Spike
        max_spike_idx = df["MoM_Growth"].idxmax()
        max_spike_row = df.loc[max_spike_idx]
        spike_label = max_spike_row["Date"].strftime("%B %Y")
        spike_val = sanitize_val(max_spike_row["MoM_Growth"])

        # 9. JSON Output Formatting
        records = []
        for _, row in df.iterrows():
            records.append({
                "Year": int(row["Year"]),
                "Month": int(row["Month"]),
                "Date": row["Date"].strftime("%Y-%m-%d"),
                "Label": row["Date"].strftime("%b %Y"),
                "Value": round(sanitize_val(row["Value"]), 2),
                "MoM_Growth": round(sanitize_val(row["MoM_Growth"]), 2),
            })

        return {
            "items_available": [str(i) for i in items],
            "selected_item": "Food Indices" if "Food Indices" in items else (str(items[0]) if items else "All Items"),
            "summary": {
                "total_months": len(df),
                "min_cpi": round(min_val, 2),
                "max_cpi": round(max_val, 2),
                "avg_cpi": round(avg_val, 2),
                "avg_monthly_growth": round(avg_growth, 2),
                "peak_spike": {
                    "label": spike_label,
                    "growth_percentage": round(spike_val, 2)
                }
            },
            "records": records
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})