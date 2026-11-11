
import json
import os
import boto3

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"

S3_PREFIX = "raw"


def save_and_upload(batch):

    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-2")

    if not bucket:
        raise ValueError("S3_BUCKET is not configured.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = batch["run_id"]

    filename = f"market_data_{run_id}.json"

    local_path = OUTPUT_DIR / filename

    # Save original JSON locally
    with open(local_path, "w") as file:
        json.dump(batch, file, indent=2)

    print(f"Saved local raw file: {local_path}")

    # Upload original JSON to S3
    s3 = boto3.client("s3", region_name=region)

    s3_key = f"{S3_PREFIX}/{filename}"

    with open(local_path, "rb") as file:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=file,
            ContentType="application/json",
            ServerSideEncryption="AES256"
        )

    s3_uri = f"s3://{bucket}/{s3_key}"

    print(f"Uploaded raw file: {s3_uri}")

    return s3_uri

