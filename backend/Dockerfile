FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT:-8000}
CMD ["sh", "-c", "\
  if [ \"$SERVERLESS\" = 'true' ] || [ \"$SERVERLESS\" = 'True' ] || [ \"$SERVERLESS\" = '1' ]; then \
    WORKERS=1; \
  else \
    WORKERS=${UVICORN_WORKERS:-4}; \
  fi && \
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers $WORKERS"]
