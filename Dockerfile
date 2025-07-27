FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies: git, curl, and gnupg2 (for adding Dart repo)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install the Dart SDK, required for the 'dart format' command in helpers.py
RUN curl https://storage.googleapis.com/dart-archive/dart-archive.key | gpg --dearmor > /usr/share/keyrings/dart-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/dart-archive-keyring.gpg] https://storage.googleapis.com/dart-archive/stable/debian stable main" > /etc/apt/sources.list.d/dart_stable.list && \
    apt-get update && apt-get install -y dart && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# NOTE: This assumes 'gitingest' is a package available on PyPI.
# If it requires a different installation method, you must modify this step.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code into the container
COPY ./hyett/ .

# The application clones git repositories into a working directory.
# Based on configs.py (WORKING_DIR = "../project_luca"), this will be created
# relative to the app's root. We create it here to be explicit.
RUN mkdir -p /app/project_luca

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Command to run the Uvicorn server when the container launches
# --host 0.0.0.0 makes the server accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]