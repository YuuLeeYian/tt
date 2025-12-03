# Use Python slim image as base
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies and gunicorn using uv in a single layer
RUN uv pip install --system --no-cache -r requirements.txt gunicorn

# Copy application files
COPY . .

# Create directory for SQLite database with proper permissions
RUN mkdir -p /app/instance && chmod 777 /app/instance

# Expose the Flask port
EXPOSE 3456

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:3456", "--workers", "4", "--timeout", "120", "app:app"]
