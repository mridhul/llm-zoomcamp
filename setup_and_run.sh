#!/bin/bash

# Exit on error
set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Upgrading pip..."
    pip install --upgrade pip
    
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "Activating existing virtual environment..."
    source venv/bin/activate
fi

echo -e "\nEnvironment setup complete!"
echo -e "\nTo run the FAQ search system, use one of the following commands:"
echo -e "1. Interactive mode: python hw.py"
echo -e "2. Single question: python hw.py \"Your question here\""
echo -e "3. With course filter: python hw.py \"Your question\" --course data-engineering-zoomcamp"
echo -e "\nDon't forget to set your GROQ_API_KEY: export GROQ_API_KEY='your-api-key-here'"

# Keep the shell open if double-clicked
$SHELL
