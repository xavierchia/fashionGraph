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

# Copy all Python files into the container
COPY *.py .

# Define the entrypoint to always run Python with unbuffered output
ENTRYPOINT ["python", "-u"]

# Define the default script to run when container starts
CMD ["reddit_demo_new.py"]