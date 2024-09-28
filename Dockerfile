# Use the official Python image as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install psutil

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the Flask app will run on
EXPOSE 5000

# Run the Python application
CMD ["python3", "webapp.py"]