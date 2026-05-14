# Use the full Python image (contains all native development package binaries)
FROM python:3.11-bookworm

WORKDIR /app

# Copy your python dependencies file
COPY requirements.txt .

# Upgrade package managers and install your project requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Crucial: --with-deps automatically downloads the exact Linux system OS
# libraries and font frameworks that Playwright needs, skipping manual apt-get.
RUN playwright install chromium --with-deps

# Copy your FastAPI app code into the container
COPY app.py .

EXPOSE 8000

# Start your web scraper endpoint
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
