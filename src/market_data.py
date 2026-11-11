
import json
import os
import time
import urllib.request
import urllib.parse

from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STOCKS_FILE = PROJECT_ROOT / "config" / "stocks.txt"

REQUEST_INTERVAL = 12


def load_tickers():
    with open(STOCKS_FILE) as file:
        tickers = [
            line.strip().upper()
            for line in file
            if line.strip()
        ]

    tickers = list(dict.fromkeys(tickers))

    if not tickers:
        raise ValueError("No stock tickers configured.")

    return tickers


def validate_results(results):
    """Perform basic source-data validation."""

    if not isinstance(results, list) or not results:
        raise ValueError("API returned no market data.")

    required_fields = ["T", "v", "o", "c", "h", "l", "t"]

    for record in results:
        missing = [
            field for field in required_fields
            if field not in record
        ]

        if missing:
            raise ValueError(f"Missing API fields: {missing}")

        for field in ["v", "o", "c", "h", "l", "t"]:
            if not isinstance(record[field], (int, float)):
                raise ValueError(f"Invalid value for {field}")

        if min(record["o"], record["c"], record["h"], record["l"]) <= 0:
            raise ValueError("Invalid stock price.")

        if record["v"] < 0:
            raise ValueError("Invalid trading volume.")

        if record["t"] <= 0:
            raise ValueError("Invalid timestamp.")

    return results


def fetch_stock_data(ticker, api_key):
    params = urllib.parse.urlencode({
        "adjusted": "true",
        "apiKey": api_key
    })

    url = (
        f"https://api.massive.com/v2/aggs/ticker/"
        f"{ticker}/prev?{params}"
    )

    request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read())

    if data.get("status") != "OK":
        raise ValueError(
            f"API returned status: {data.get('status')}"
        )

    results = validate_results(data.get("results"))

    return results


def fetch_market_data():
    api_key = os.getenv("MASSIVE_API_KEY")

    if not api_key:
        raise ValueError("MASSIVE_API_KEY is not configured.")

    tickers = load_tickers()

    run_id = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    batch = {
        "run_id": run_id,
        "ingestion_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "Massive",
        "requested_tickers": tickers,
        "successful_stocks": {},
        "failures": []
    }

    print(f"Retrieving data for {len(tickers)} stocks.")

    for index, ticker in enumerate(tickers):

        print(f"Retrieving {ticker}...")

        try:
            results = fetch_stock_data(ticker, api_key)

            batch["successful_stocks"][ticker] = results

            print(f"Success: {len(results)} record(s)")

        except Exception as error:
            batch["failures"].append({
                "ticker": ticker,
                "error": str(error)
            })

            print(f"Failed: {error}")

        if index < len(tickers) - 1:
            time.sleep(REQUEST_INTERVAL)

    return batch

