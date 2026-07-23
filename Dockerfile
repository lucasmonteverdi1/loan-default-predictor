FROM python:3.11-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build context is the repo root (loan-default-predictor/) so model/ is reachable.
COPY model/ ./model/

COPY backend/app/ ./app/

USER appuser

ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --log-level info"]
