FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure poetry: no virtualenvs in container
RUN poetry config virtualenvs.create false

# Install dependencies (skip dev deps for prod, include for dev)
RUN poetry install --no-interaction --no-ansi --no-root || \
    poetry install --no-interaction --no-ansi --no-root --no-dev 2>/dev/null || true

# Copy application code
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi --only-root 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
