FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# tesseract-ocr enables the OCR fallback for scanned PDFs.
# graphviz renders the HLD dependency map.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        graphviz \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ui ./ui
COPY scripts ./scripts
COPY data/samples ./data/samples

RUN mkdir -p /app/data/vectorstore /app/data/uploads /app/.cache/huggingface

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
