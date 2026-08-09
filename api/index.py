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

        # Extract items
        items = raw_df["Item"].dropna().unique().tolist() if "Item" in raw_df.columns else []

        if "Food Indices" in items:
            df = raw_df[raw_df["Item"] == "Food Indices"].copy()
        elif items:
            df = raw_df[raw_df["Item"] == items[0]].copy()
        else:
            df = raw_df.copy()

        # Clean numeric columns
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

        # Decode Month Codes
        if "Months Code" in df.columns:
            df["Months Code"] = pd.to_numeric(df["Months Code"], errors="coerce")
            df["Month"] = df["Months Code"] - 7000
        elif "Month" in df.columns:
            df["Month"] = pd.to_numeric(df["Month"], errors="coerce")

        # Drop invalid rows and sort
        df = df.dropna(subset=["Year", "Month", "Value"])
        df = df.sort_values(by=["Year", "Month"]).reset_index(drop=True)

        if df.empty:
            return JSONResponse(status_code=400, content={"error": "No valid data rows found in CSV."})

        # Build Datetime
        df["Date"] = pd.to_datetime(
            df["Year"].astype(int).astype(str) + "-" + df["Month"].astype(int).astype(str) + "-01",
            errors="coerce"
        )
        df = df.dropna(subset=["Date"])

        # Calculate MoM Growth
        df["MoM_Growth"] = (df["Value"].pct_change() * 100).fillna(0.0).round(2)

        # Statistical Calculations safely
        min_val = sanitize_val(df["Value"].min())
        max_val = sanitize_val(df["Value"].max())
        avg_val = sanitize_val(df["Value"].mean())
        avg_growth = sanitize_val(df["MoM_Growth"].mean())

        # Peak Spike calculation
        max_spike_idx = df["MoM_Growth"].idxmax()
        max_spike_row = df.loc[max_spike_idx]
        spike_label = max_spike_row["Date"].strftime("%B %Y")
        spike_val = sanitize_val(max_spike_row["MoM_Growth"])

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