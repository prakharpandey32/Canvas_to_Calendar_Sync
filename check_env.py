import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

p = Path(".env")
print("ENV exists:", p.exists(), "size:", p.stat().st_size if p.exists() else 0)

vals = dotenv_values(p)
print("keys:", list(vals.keys()))
print("token_len_in_file:", len((vals.get("CANVAS_API_TOKEN") or "")))

os.environ.pop("CANVAS_BASE_URL", None)
os.environ.pop("CANVAS_API_TOKEN", None)
ok = load_dotenv(p, override=True)
print("load_dotenv returned:", ok)
print("URL from os.getenv:", os.getenv("CANVAS_BASE_URL"))
print("TOKEN_LEN from os.getenv:", len(os.getenv("CANVAS_API_TOKEN") or ""))
