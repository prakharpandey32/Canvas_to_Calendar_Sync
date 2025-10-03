import os, requests
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

ENV_PATH = Path(__file__).with_name(".env")  # load .env next to this file
print("ENV_PATH:", ENV_PATH.resolve(), "exists:", ENV_PATH.exists())
print("dotenv_values token_len_in_file:", len((dotenv_values(ENV_PATH).get("CANVAS_API_TOKEN") or "")))

# override=True so empty shell vars cannot block .env values
load_dotenv(dotenv_path=ENV_PATH, override=True)

base = (os.getenv("CANVAS_BASE_URL") or "").rstrip("/")
token = os.getenv("CANVAS_API_TOKEN") or ""
print("os.getenv token_len:", len(token), "base_ok:", bool(base))

assert base and token, "Missing CANVAS_BASE_URL or CANVAS_API_TOKEN"

r = requests.get(f"{base}/api/v1/users/self/profile",
                 headers={"Authorization": f"Bearer {token}"}, timeout=30)
print("STATUS:", r.status_code)
print("NAME:", r.json().get("name") if r.ok else r.text)
