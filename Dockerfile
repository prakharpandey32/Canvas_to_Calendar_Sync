FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose port
EXPOSE 8000

# Set environment for HTTP mode
ENV MCP_TRANSPORT=sse
ENV PORT=8000

# Run server
CMD ["python", "server.py"]
