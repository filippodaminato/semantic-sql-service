FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip and dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using pip (since we're using pyproject.toml)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    sqlalchemy==2.0.23 \
    alembic==1.12.1 \
    psycopg2-binary==2.9.9 \
    "pydantic[email]==2.5.0" \
    pydantic-settings==2.1.0 \
    openai>=1.12.0 \
    sqlglot==20.1.0 \
    pgvector==0.2.3 \
    python-multipart==0.0.6 \
    httpx==0.27.0 \
    pytest \
    pytest-asyncio \
    pytest-cov

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
