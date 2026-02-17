#!/bin/bash
set -e

# Basic entrypoint script
# Can add migration commands here if needed in the future

echo "Starting Job Board API..."

# Start Uvicorn
exec uvicorn main:app --host 0.0.0.0 --port 8000
