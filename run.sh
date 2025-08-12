#!/bin/bash

# Exit if any command fails
set -e

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Run FastAPI server
echo "Starting FastAPI app..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
