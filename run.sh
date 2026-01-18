#!/bin/bash

# Check if yt-dlp is installed and update it
if ! command -v yt-dlp &> /dev/null
then
    echo "❌ yt-dlp not found. Installing..."
    pip install yt-dlp
else
    echo "🔄 Checking for yt-dlp updates..."
    pip install -U yt-dlp &> /dev/null
fi

# Run the python script
python3 downloader.py
