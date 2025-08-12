#!/bin/bash

# Exit if any command fails
set -e

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install required packages
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Build complete! To start the server, run:"
echo "source venv/bin/activate && uvicorn main:app --reload"
