# ---- Build Stage ----
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env var automatically
ENV PORT=8000

# Expose the port
EXPOSE ${PORT}

# Run the server
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
