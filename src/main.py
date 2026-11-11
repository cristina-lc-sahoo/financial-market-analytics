
import os
import subprocess
import sys

from dotenv import load_dotenv

from src.market_data import fetch_market_data
from src.storage import save_and_upload
from src.json_to_parquet import main as convert_json_to_parquet


def run_dbt():
    """Run dbt transformations and data quality tests."""

    dbt_dir = os.path.join(os.getcwd(), "dbt")

    dbt_executable = os.path.join(
        os.path.dirname(sys.executable),
        "dbt"
    )

    print("\nRunning dbt transformations...")

    subprocess.run(
        [dbt_executable, "run", "--project-dir", dbt_dir],
        check=True
    )

    print("\nRunning dbt tests...")

    subprocess.run(
        [dbt_executable, "test", "--project-dir", dbt_dir],
        check=True
    )

def main():
    load_dotenv("config/.env",override=True)

    print("=" * 60)
    print("FINANCIAL MARKET ANALYTICS PIPELINE")
    print("=" * 60)

    try:
        # Step 1: Extract market data
        print("\nSTEP 1: Fetching market data from Massive API...")

        batch = fetch_market_data()

        if not batch:
            raise RuntimeError("No market data returned from Massive API.")

        # Step 2: Save raw JSON to S3
        print("\nSTEP 2: Uploading raw JSON to S3...")

        save_and_upload(batch)

        # Step 3: Convert raw JSON to Parquet
        print("\nSTEP 3: Converting raw JSON to Parquet...")

        convert_json_to_parquet()

        # Step 4: Run dbt transformations and tests
        if os.getenv("RUN_DBT", "true").lower() == "true":
            print("\nSTEP 4: Running dbt...")

            run_dbt()
        else:
            print("\nSTEP 4: dbt execution skipped (RUN_DBT=false).")

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}")
        raise


if __name__ == "__main__":
    main()

