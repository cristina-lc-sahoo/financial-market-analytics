
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "config" / ".env"


def load_api_key():
    with open(ENV_FILE) as file:
        for line in file:
            if line.startswith("MASSIVE_API_KEY="):
                return line.strip().split("=", 1)[1]

    raise ValueError("MASSIVE_API_KEY not found in config/.env")


def main():
    api_key = load_api_key()

    params = urllib.parse.urlencode({
        "adjusted": "true",
        "apiKey": api_key
    })

    url = f"https://api.massive.com/v2/aggs/ticker/AAPL/prev?{params}"

    request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read())

    if data.get("status") == "OK" and data.get("results"):
        print("API connection successful!")
        print(f"Stock: AAPL")
        print(f"Records returned: {len(data['results'])}")
        print(f"Data: {data['results'][0]}")
    else:
        print("API request completed, but no market data was returned.")
        print(data)


if __name__ == "__main__":
    main()

