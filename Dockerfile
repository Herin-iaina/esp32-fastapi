
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Environment variable to choose mode: http, mqtt, or both
# - http (default): Lance l'API FastAPI
# - mqtt: Lance le middleware MQTT
# - both: Lance les deux services
ENV MODE=http

# Run entrypoint script when the container launches
ENTRYPOINT ["/app/entrypoint.sh"]
