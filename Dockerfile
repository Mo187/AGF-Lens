# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Copy dependency list and install them
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Cloud Run will use (Cloud Run sets PORT env variable automatically)
EXPOSE 8080

# Start Gunicorn using our configuration and our Flask app (assumes your app is defined in run.py as "app")
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
