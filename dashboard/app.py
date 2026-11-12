import time

import boto3
import pandas as pd
import plotly.express as px
import streamlit as st

# AWS configuration
AWS_REGION = "us-east-2"
DATABASE = "market_analytics"
TABLE = "stock_daily_summary"
RESULTS_LOCATION = (
    "s3://financial-market-analytics-raw-789942391442-us-east-2-an/"
    "athena-results/"
)

st.set_page_config(
    page_title="Financial Market Analytics",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Financial Market Analytics")
st.caption("AWS Athena · S3 · dbt · Streamlit")

@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data():
    client = boto3.client("athena", region_name=AWS_REGION)

    query = f"""
        SELECT
            ticker,
            trade_date,
            average_close,
            highest_price,
            lowest_price,
            total_volume,
            total_transactions,
            average_vwap
        FROM {TABLE}
        WHERE CAST(trade_date AS DATE) >=
              date_add('day', -365, current_date)
        ORDER BY trade_date, ticker
    """

    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": RESULTS_LOCATION},
        WorkGroup="primary"
    )

    query_id = response["QueryExecutionId"]

    # Wait for Athena to finish
    for _ in range(120):
        status = client.get_query_execution(
            QueryExecutionId=query_id
        )["QueryExecution"]["Status"]

        state = status["State"]

        if state == "SUCCEEDED":
            break

        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(status.get("StateChangeReason", state))

        time.sleep(2)
    else:
        raise TimeoutError("Athena query timed out.")

    # Retrieve all result pages
    rows = []
    next_token = None

    while True:
        args = {"QueryExecutionId": query_id}
        if next_token:
            args["NextToken"] = next_token

        result = client.get_query_results(**args)
        page_rows = result["ResultSet"]["Rows"]

        if not rows:
            page_rows = page_rows[1:]  # Skip column headers

        for row in page_rows:
            values = [
                cell.get("VarCharValue", "")
                for cell in row["Data"]
            ]
            rows.append(values)

        next_token = result.get("NextToken")
        if not next_token:
            break

    columns = [
        "ticker", "trade_date", "average_close",
        "highest_price", "lowest_price", "total_volume",
        "total_transactions", "average_vwap"
    ]

    df = pd.DataFrame(rows, columns=columns)

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    numeric_columns = [
        "average_close", "highest_price", "lowest_price",
        "total_volume", "total_transactions", "average_vwap"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


# Refresh controls
if st.sidebar.button("🔄 Refresh Data"):
    load_stock_data.clear()

try:
    with st.spinner("Retrieving stock data from AWS Athena..."):
        df = load_stock_data()

except Exception as error:
    st.error(f"Unable to load data from Athena: {error}")
    st.stop()

if df.empty:
    st.warning("No stock records were returned.")
    st.stop()

# Sidebar filters
st.sidebar.header("Dashboard Filters")

tickers = sorted(df["ticker"].unique())

selected_tickers = st.sidebar.multiselect(
    "Select stocks",
    tickers,
    default=tickers
)

if not selected_tickers:
    st.warning("Select at least one stock.")
    st.stop()

filtered = df[df["ticker"].isin(selected_tickers)].copy()

# Summary metrics
latest_date = filtered["trade_date"].max()
latest = filtered[filtered["trade_date"] == latest_date]

col1, col2, col3 = st.columns(3)

col1.metric("Latest Trading Date", latest_date.strftime("%b %d, %Y"))
col2.metric("Stocks Selected", len(selected_tickers))
col3.metric("Records Loaded", f"{len(filtered):,}")

st.divider()

# Closing price chart
st.subheader("Stock Closing Prices")

price_chart = px.line(
    filtered,
    x="trade_date",
    y="average_close",
    color="ticker",
    markers=True,
    labels={
        "trade_date": "Trading Date",
        "average_close": "Average Close ($)",
        "ticker": "Stock"
    }
)

price_chart.update_layout(hovermode="x unified")
st.plotly_chart(price_chart, use_container_width=True)

# Trading volume chart
st.subheader("Trading Volume")

volume_chart = px.line(
    filtered,
    x="trade_date",
    y="total_volume",
    color="ticker",
    markers=True,
    labels={
        "trade_date": "Trading Date",
        "total_volume": "Trading Volume",
        "ticker": "Stock"
    }
)

volume_chart.update_layout(hovermode="x unified")
st.plotly_chart(volume_chart, use_container_width=True)

# Latest stock details
st.subheader("Latest Stock Summary")

summary = latest[
    [
        "ticker", "average_close", "highest_price",
        "lowest_price", "total_volume", "total_transactions"
    ]
].sort_values("ticker")

st.dataframe(summary, use_container_width=True, hide_index=True)

st.caption(
    "Data source: AWS Athena | "
    "Database: market_analytics | "
    "Table: stock_daily_summary | "
    "Refresh cache: 15 minutes"
)
