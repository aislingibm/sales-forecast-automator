# Hardened minimal Red Hat UBI container image
FROM registry.redhat.io/ubi9/python-311-minimal:latest

# Create unprivileged non-root application user
RUN useradd -m -u 1001 appuser

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . .

# Ensure data and outbox directories exist with write permissions
RUN mkdir -p /app/data/snapshots /app/outbox && chown -R appuser:appuser /app

# Switch to non-root user
USER 1001

# Expose HTTP port
EXPOSE 8000

# Start FastAPI application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
