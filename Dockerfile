# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Optional (safer build for packages that need compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first to leverage Docker layer caching
COPY pyproject.toml ./
RUN python -m pip install --upgrade pip \
 && pip install "mcp[cli]" requests python-dotenv beautifulsoup4 pdfminer.six dateparser \
                google-api-python-client google-auth-httplib2 google-auth-oauthlib msal

# Then copy source
COPY server.py ./

# Default start command (Smithery can override)
CMD ["python", "server.py"]
