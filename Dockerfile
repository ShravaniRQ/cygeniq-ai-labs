# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Install Node.js 20 (required for npx MCP servers)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies first (for better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install the npx MCP packages so they don't need to download at runtime
RUN npx -y @modelcontextprotocol/server-filesystem --help || true
RUN npx -y @modelcontextprotocol/server-postgres --help || true
RUN npx -y @modelcontextprotocol/server-memory --help || true

# Copy the rest of the application code
COPY agent.py server.py ./
COPY static/ ./static/
COPY policies/ ./policies/

# Expose the port Uvicorn will run on
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
