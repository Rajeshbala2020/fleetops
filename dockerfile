# Use a slim, recent Python that all your pins support
FROM python:3.11-slim

# System deps your list may need (pyodbc, numpy/scipy wheels, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    unixodbc unixodbc-dev \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Keep images small and deterministic
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN python -m pip install -U pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# HF Spaces sets $PORT; bind to it. Default to 7860 locally.
ENV PORT=7860
EXPOSE 7860

# Start your ASGI app. If Flask, switch to gunicorn.
CMD ["bash", "-lc", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
