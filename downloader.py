#!/usr/bin/env python3
"""
Batch downloader using yt-dlp.

Steps implemented:
1. Read links from `link.txt` (one URL per line).
2. For each link:
   - Verify link exists and is non-empty.
   - Use `yt-dlp --dump-json` to fetch structured format info.
   - Pick the highest-quality video-only and audio-only formats (preferring resolution/bitrate).
   - If no separate video/audio found, fall back to a single best format.
   - Download with the selected format and merge via ffmpeg.
3. Save downloaded files into a dedicated 'downloads' folder.
"""

