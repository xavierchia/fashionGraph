# Use Python 3.11 slim image as the base - smaller footprint than full Python image
FROM python:3.11-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Copy requirements file first to leverage Docker layer caching
# If dependencies haven't changed, this layer will be cached and pip install skipped
COPY requirements.txt .

# Install Python dependencies without caching to reduce image size
# --no-cache-dir prevents pip from storing downloaded packages locally
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application file into the container
COPY reddit_demo.py .

# Set environment variable to ensure Python output is sent directly to terminal
# This prevents buffering of stdout/stderr in Docker containers
ENV PYTHONUNBUFFERED=1

# Define the default command to run when container starts
CMD ["python", "reddit_demo.py"]