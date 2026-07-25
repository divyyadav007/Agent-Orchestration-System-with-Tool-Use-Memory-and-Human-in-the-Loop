FROM python:3.11-slim

# Prevent Python from writing .pyc files and force unbuffered stdout/stderr logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install build tools and dependencies for ChromaDB and Sentence-Transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose Streamlit default production port
EXPOSE 8501

# Launch Streamlit app bound to 0.0.0.0
CMD ["streamlit", "run", "frontend/review-ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
