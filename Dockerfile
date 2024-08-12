# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Install supervisord, Redis, and the supervisor Python package
RUN apt-get update && apt-get install -y supervisor redis-server && pip install supervisor

# Copy the supervisord configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create a directory for Redis data
RUN mkdir -p /data/redis

# Expose the ports for the app and Redis
EXPOSE 5000 6379

# Specify the command to run supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]