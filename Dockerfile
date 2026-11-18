
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

# Create a non-root application user
RUN useradd --create-home appuser

# Install CPU-only PyTorch first
RUN pip install --upgrade pip && \
    pip install --index-url https://download.pytorch.org/whl/cpu torch

# Install application dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application and required RAG modules
COPY app.py .
COPY src/rag ./src/rag

# Copy the prebuilt vector index
COPY data/processed/vector_index ./data/processed/vector_index

# Set permissions
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
