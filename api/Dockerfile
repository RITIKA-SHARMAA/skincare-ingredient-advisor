FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e . && useradd --create-home app && mkdir -p /app/storage && chown app /app/storage
USER app
EXPOSE 8000
# Cloud Run sets PORT; locally it defaults to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
