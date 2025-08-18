#!/bin/bash

# Clean up any existing Xvfb locks
rm -f /tmp/.X99-lock

# Start Xvfb virtual display server in background
Xvfb :99 -screen 0 1024x768x24 &

# Wait a moment for Xvfb to start
sleep 2

# Create matplotlib config directory in user home
mkdir -p /home/manimpro/.matplotlib

# Switch to manimpro user and start the Python application
exec su manimpro -c "python -m uvicorn src.main:app --host 0.0.0.0 --port 8000" 