# Use the official Python image as the base image
FROM python:3.12-slim

# Install nginx
RUN apt-get update && apt-get install -y nginx

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install psutil

# Copy the rest of the application code into the container
COPY . .

# Copy the nginx configuration file
COPY ngnix.conf /etc/nginx/nginx.conf

# Only expose port 80 because nginx will proxy the requests to the Flask app on port 5000
EXPOSE 80

# Copy the startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Run the startup script
CMD ["/start.sh"]