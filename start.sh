#!/bin/bash

echo "Starting the webapp..."

# Start the Python webapp in the background
python3 webapp.py &

echo "Starting nginx..."
# Start nginx in the foreground
nginx -g 'daemon off;' &

# Wait for the webapp to start
sleep 10

echo "Webapp and nginx started"

# Keep the script running
tail -f /dev/null
