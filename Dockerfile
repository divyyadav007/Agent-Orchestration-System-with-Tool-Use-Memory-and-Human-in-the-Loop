# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for chroma and sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

EXPOSE 7860

# Run the Streamlit frontend app using dynamic port binding and disabling CORS/XSRF for proxy routing compatibility
CMD ["sh", "-c", "streamlit run frontend/review-ui/app.py --server.port=${PORT:-7860} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false"]
