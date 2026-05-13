FROM mcr.microsoft.com/playwright:v1.52.0-noble

WORKDIR /app

# Copy your dependency requirements manifest
COPY requirements.txt .

# Upgrade package installers and compile your Python requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# The Microsoft image already includes the core browser bundles natively,
# but we run the installer to link configuration versions perfectly.
RUN playwright install chromium

# Copy your application script code 
COPY app.py .

EXPOSE 8000

# Start your web crawler server interface
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
