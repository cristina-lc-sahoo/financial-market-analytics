
import json
import os
from io import BytesIO
from pathlib import PurePosixPath

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv


load_dotenv("config/.env")

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET")

RAW_PREFIX = os.getenv("S3_RAW_PREFIX", "raw/").strip("/") + "/"
PROCESSED_PREFIX = os.getenv(
    "S3_PROCESSED_PREFIX", "processed/"
).strip("/") + "/"

if not S3_BUCKET:
    raise ValueError("Missing S3_BUCKET in config/.env")


# Output schema: one row per ticker and market record.
SCHEMA = pa.schema([
    ("ingestion_timestamp", pa.string()),
    ("source", pa.string()),
    ("source_file", pa.string()),
    ("ticker", pa.string()),
    ("volume", pa.float64()),
    ("vwap", pa.float64()),
    ("open", pa.float64()),
    ("close", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("timestamp_ms", pa.int64()),
    ("transactions", pa.int64()),
])


def to_float(value):
    if value is None:
        return None
    return float(value)


def to_int(value):
    if value is None:
        return None
    return int(value)


def flatten_json(data, source_file):
    rows = []

    ingestion_timestamp = data.get("ingestion_timestamp")
    source = data.get("source")

    successful_stocks = data.get("successful_stocks", {})

    for ticker, records in successful_stocks.items():

        if not isinstance(records, list):
            continue

        for record in records:

            rows.append({
                "ingestion_timestamp": ingestion_timestamp,
                "source": source,
                "source_file": source_file,
                "ticker": ticker,
                "volume": to_float(record.get("v")),
                "vwap": to_float(record.get("vw")),
                "open": to_float(record.get("o")),
                "close": to_float(record.get("c")),
                "high": to_float(record.get("h")),
                "low": to_float(record.get("l")),
                "timestamp_ms": to_int(record.get("t")),
                "transactions": to_int(record.get("n")),
            })

    return rows


def process_json_file(s3_client, key):

    print(f"\nReading: {key}")

    response = s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=key
    )

    data = json.loads(response["Body"].read().decode("utf-8"))

    rows = flatten_json(data, PurePosixPath(key).name)

    if not rows:
        print("No market records found. Skipping file.")
        return

    table = pa.Table.from_pylist(rows, schema=SCHEMA)

    parquet_buffer = BytesIO()

    pq.write_table(
        table,
        parquet_buffer,
        compression="snappy"
    )

    output_name = PurePosixPath(key).stem + ".parquet"
    output_key = PROCESSED_PREFIX + output_name

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=parquet_buffer.getvalue(),
        ContentType="application/vnd.apache.parquet"
    )

    print(f"Rows converted: {len(rows)}")
    print(f"Uploaded: s3://{S3_BUCKET}/{output_key}")


def main():

    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION
    )

    paginator = s3_client.get_paginator("list_objects_v2")

    total_files = 0

    print("=" * 55)
    print("JSON TO PARQUET TRANSFORMATION")
    print("=" * 55)

    for page in paginator.paginate(
        Bucket=S3_BUCKET,
        Prefix=RAW_PREFIX
    ):

        for item in page.get("Contents", []):

            key = item["Key"]

            if not key.lower().endswith(".json"):
                continue

            process_json_file(s3_client, key)
            total_files += 1

    print("\n" + "=" * 55)
    print(f"Transformation completed. Files processed: {total_files}")
    print(f"Output location: s3://{S3_BUCKET}/{PROCESSED_PREFIX}")
    print("=" * 55)


if __name__ == "__main__":
    main()

