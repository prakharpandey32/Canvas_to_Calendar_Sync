# Simple, reliable Python base
FROM python:3.11-slim

# Faster, cleaner Python runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your server
COPY server.py ./

# Defaults for HTTP MCP
ENV MCP_TRANSPORT=http
ENV PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
