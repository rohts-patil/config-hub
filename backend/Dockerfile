FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Ensure packaging tools are available for the local project install
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY . .

# Install the app and its dependencies after source files are present
RUN pip install --no-cache-dir --no-build-isolation .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
