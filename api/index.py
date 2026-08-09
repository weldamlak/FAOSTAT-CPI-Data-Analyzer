from io import BytesIO
from fastapi import FastAPI, File, UploadFile
import pandas as pd

app = FastAPI()


@app.post("/api/analyze-fao-cpi")
async def analyze_fao_cpi(file: UploadFile = File(...)):
    # 1. Read CSV into memory
    contents = await file.read()
    raw_df = pd.read_csv(BytesIO(contents))

    # 2. Extract and filter unique CPI items/categories
    items = (
        raw_df["Item"].dropna().unique().tolist() if "Item" in raw_df.columns else []
    )

    if "Food Indices" in items:
        df = raw_df[raw_df["Item"] == "Food Indices"].copy()
    elif items:
        df = raw_df[raw_df["Item"] == items[0]].copy()
    else:
        df = raw_df.copy()

    # 3. Clean numeric fields
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

    # 4. Decode FAOSTAT Month Codes (7001 -> 1, 7012 -> 12)
    if "Months Code" in df.columns:
        df["Months Code"] = pd.to_numeric(df["Months Code"], errors="coerce")
        df["Month"] = df["Months Code"] - 7000
    elif "Month" in df.columns:
        df["Month"] = pd.to_numeric(df["Month"], errors="coerce")

    # 5. Drop invalid rows and sort chronologically
    df = df.dropna(subset=["Year", "Month", "Value"])
    df = df.sort_values(by=["Year", "Month"]).reset_index(drop=True)

    # 6. Build Datetime Column
    df["Date"] = pd.to_datetime(
        df["Year"].astype(int).astype(str)
        + "-"
        + df["Month"].astype(int).astype(str)
        + "-01"
    )

    # 7. Calculate Month-over-Month Growth Rate %
    df["MoM_Growth_%"] = (df["Value"].pct_change() * 100).fillna(0).round(2)

    # 8. Statistical Calculations
    min_val = float(df["Value"].min())
    max_val = float(df["Value"].max())
    avg_val = float(df["Value"].mean())
    avg_growth = float(df["MoM_Growth_%"].mean())

    # Find Highest Inflation Spike
    max_spike_idx = df["MoM_Growth_%"].idxmax()
    max_spike_row = df.loc[max_spike_idx]
    spike_label = max_spike_row["Date"].strftime("%B %Y")
    spike_val = float(max_spike_row["MoM_Growth_%"])

    # 9. Format records for Next.js UI
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "Year": int(row["Year"]),
                "Month": int(row["Month"]),
                "Date": row["Date"].strftime("%Y-%m-%d"),
                "Label": row["Date"].strftime("%b %Y"),
                "Value": round(float(row["Value"]), 2),
                "MoM_Growth": round(float(row["MoM_Growth_%"]), 2),
            }
        )

    return {
        "items_available": items,
        "selected_item": (
            "Food Indices"
            if "Food Indices" in items
            else (items[0] if items else "All Items")
        ),
        "summary": {
            "total_months": len(df),
            "min_cpi": round(min_val, 2),
            "max_cpi": round(max_val, 2),
            "avg_cpi": round(avg_val, 2),
            "avg_monthly_growth": round(avg_growth, 2),
            "peak_spike": {"label": spike_label, "growth_percentage": spike_val},
        },
        "records": records,
    }