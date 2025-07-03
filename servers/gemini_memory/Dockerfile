FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install -r requirements.txt

FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Default configuration
ENV MCP_CONFIG_DIR=/app/config
ENV MCP_DATA_DIR=/app/data
ENV MEMORY_FILE_PATH=/app/data/memory.json

# Create necessary directories
RUN mkdir -p /app/config /app/data /app/cache

# Set permissions
RUN chmod +x setup.sh

# Create volume mount points for persistence
VOLUME ["/app/config", "/app/data"]

ENTRYPOINT ["python", "-m", "memory_mcp"]