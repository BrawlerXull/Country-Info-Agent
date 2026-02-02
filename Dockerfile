FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects PORT env var; default to 8000 for local dev
ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn country_info_agent.api:app --host 0.0.0.0 --port ${PORT}
