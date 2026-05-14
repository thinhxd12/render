FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/list/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run Crawl4AI system installation and setup playwright components
RUN crawl4ai-setup
RUN python -m playwright install --with-deps chromium

# Copy application source code
COPY app.py .

# Expose default Render port
EXPOSE 10000

CMD ["python", "app.py"]
