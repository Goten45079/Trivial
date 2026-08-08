FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/llm_lens.db

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY index.html ./
COPY src ./src
RUN mkdir -p /app/data && chown -R app:app /app
USER app
EXPOSE 8000
VOLUME ["/app/data"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
