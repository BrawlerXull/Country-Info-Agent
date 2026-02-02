FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run tests during build - build fails if tests fail
RUN python -m pytest tests/ -v --tb=short

# Render injects PORT env var; default to 8000 for local dev
ENV PORT=8000
EXPOSE 8000

# Use shell form with exec for proper signal handling and variable expansion
CMD ["sh", "-c", "exec uvicorn country_info_agent.api:app --host 0.0.0.0 --port ${PORT}"]
