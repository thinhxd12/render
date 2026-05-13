# Use the official pre-configured Playwright Python image
FROM microsoft.com

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and install your python requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# The base image already has chromium, but we ensure it matches the library version
RUN playwright install chromium

COPY app.py .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
