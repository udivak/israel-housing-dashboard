# Stage 1: Python package builder
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: runtime image
# Playwright's Chromium browser binaries and their system-level library
# dependencies must live in the runtime layer — they cannot simply be copied
# from the builder stage.
FROM python:3.12-slim

RUN addgroup --system app && adduser --system --ingroup app app

# Install Chromium system library dependencies required by Playwright.
# These are the libraries that Chromium links against at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Download Chromium browser binaries as the app user.
# playwright install writes to ~/.cache/ms-playwright which is owned by the
# running user, so this must happen after USER is set.
USER app
RUN playwright install chromium

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
