FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch from the CPU-only index first — skips ~2GB of unused CUDA wheels (this
# service does CPU inference). Satisfies the torch>=2.0 line below as a no-op.
RUN pip install --no-cache-dir --timeout 300 --retries 5 \
        --index-url https://download.pytorch.org/whl/cpu "torch>=2.0"
RUN pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

COPY . .

EXPOSE 8002
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8002"]
