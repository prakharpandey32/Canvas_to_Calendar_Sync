FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 8000

# Use stdio - simpler and more reliable
ENV MCP_TRANSPORT=stdio
CMD ["python", "server.py"]
