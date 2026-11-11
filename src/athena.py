
import os
import time
import boto3


def get_athena_client():
    return boto3.client(
        "athena",
        region_name=os.getenv("AWS_REGION", "us-east-2")
    )


def get_athena_config():
    bucket = os.getenv("S3_BUCKET")

    if not bucket:
        raise ValueError("S3_BUCKET is missing")

    return {
        "database": os.getenv(
            "ATHENA_DATABASE", "market_analytics"
        ),
        "workgroup": os.getenv(
            "ATHENA_WORKGROUP", "primary"
        ),
        "output": os.getenv(
            "ATHENA_OUTPUT_LOCATION",
            f"s3://{bucket}/athena-results/"
        )
    }


def execute_query(query, database=None):
    client = get_athena_client()
    config = get_athena_config()

    params = {
        "QueryString": query,
        "WorkGroup": config["workgroup"],
        "ResultConfiguration": {
            "OutputLocation": config["output"]
        }
    }

    if database:
        params["QueryExecutionContext"] = {
            "Database": database
        }

    response = client.start_query_execution(**params)
    query_id = response["QueryExecutionId"]

    while True:
        result = client.get_query_execution(
            QueryExecutionId=query_id
        )

        status = result["QueryExecution"]["Status"]["State"]

        if status == "SUCCEEDED":
            print(f"Athena query succeeded: {query_id}")
            return query_id

        if status in ("FAILED", "CANCELLED"):
            reason = result["QueryExecution"]["Status"].get(
                "StateChangeReason", "Unknown error"
            )
            raise RuntimeError(f"Athena query failed: {reason}")

        time.sleep(2)


def create_database():
    config = get_athena_config()

    execute_query(
        f"CREATE DATABASE IF NOT EXISTS {config['database']}"
    )

    print(f"Database ready: {config['database']}")

