FROM python:3.11-slim

WORKDIR /locust

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy locustfile
COPY locustfile.py .

# Expose Locust web UI port
EXPOSE 8089

# Run Locust
# Can be overridden with different parameters
CMD ["locust", "-f", "locustfile.py", "--host=http://api:8000"]
