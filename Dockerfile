ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create workspace and ensure config directory exists
RUN mkdir -p workspace config

# Copy the application code
COPY core core/
COPY config config/
COPY bespoke_code.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WORKSPACE_DIR=/app/workspace
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "bespoke_code.py"] 