#!/bin/bash

# Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null
then
    echo "❌ yt-dlp not found. Installing..."
    pip install yt-dlp
fi

# Run the python script
python3 downloader.py
