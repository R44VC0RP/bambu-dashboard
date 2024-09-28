#!/bin/bash

echo "Starting the webapp..."

# Start the Python webapp in the background
python3 webapp.py &

echo "Starting nginx..."
# Start nginx in the foreground
nginx -g 'daemon off;'