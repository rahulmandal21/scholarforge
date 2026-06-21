# ScholarForge backend — Dockerfile for Hugging Face Spaces
# Hugging Face Spaces (Docker SDK) requires the app to listen on port 7860,
# and only /tmp is writable at runtime — both are handled below.

FROM python:3.11-slim

WORKDIR /app

# System deps some Python packages need to build/run cleanly
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces only allows writes to /tmp — point our data dirs there
ENV UPLOAD_DIR=/tmp/uploads
ENV CHROMA_PERSIST_DIR=/tmp/chroma_db
RUN mkdir -p /tmp/uploads /tmp/chroma_db

# Hugging Face Spaces expects the app on port 7860
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
