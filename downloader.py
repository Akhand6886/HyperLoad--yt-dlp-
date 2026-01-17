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

import subprocess
import sys
import json
import shutil
from pathlib import Path

# Configuration
LINK_FILE = Path("link.txt")
DOWNLOAD_DIR = Path("downloads")
OUTPUT_TEMPLATE = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

def check_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print("✅ ffmpeg found:", ffmpeg_path)
        return True
    else:
        print("⚠️ ffmpeg not found. Merging may fail if separate streams are downloaded.")
        print("   Install ffmpeg: brew install ffmpeg")
        return False

def read_links(file_path: Path):
    if not file_path.exists():
        # Create empty file if it doesn't exist
        file_path.touch()
        print(f"📝 Created {file_path}. Please add URLs to it.")
        return []
    with file_path.open("r", encoding="utf-8") as f:
        lines = [line.split("#", 1)[0].strip() for line in f]
    links = [l for l in lines if l]
    return links

def fetch_formats_json(url: str):
    cmd = ["yt-dlp", "--dump-json", url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"❌ yt-dlp failed to fetch info for {url}")
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print("❌ Failed to parse yt-dlp JSON output:", e)
        return None

def choose_best_streams(formats: list):
    video_only = []
    audio_only = []
    single_av = []

    for f in formats:
        fmt_id = str(f.get("format_id"))
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")

        if vcodec and vcodec != "none" and (not acodec or acodec == "none"):
            score = f.get("height") or f.get("tbr") or 0
            video_only.append((score, fmt_id))
        elif acodec and acodec != "none" and (not vcodec or vcodec == "none"):
            score = f.get("abr") or f.get("tbr") or 0
            audio_only.append((score, fmt_id))
        elif vcodec and vcodec != "none" and acodec and acodec != "none":
            score = f.get("height") or f.get("tbr") or 0
            single_av.append((score, fmt_id))

    video_only.sort(key=lambda x: x[0])
    audio_only.sort(key=lambda x: x[0])
    single_av.sort(key=lambda x: x[0])

    if video_only and audio_only:
        return video_only[-1][1], audio_only[-1][1], None
    if single_av:
        return None, None, single_av[-1][1]
    
    v_id = video_only[-1][1] if video_only else None
    a_id = audio_only[-1][1] if audio_only else None
    return v_id, a_id, None

def download_with_format(url: str, format_code: str):
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f",
        format_code,
        "--merge-output-format", "mp4",
        "-o", OUTPUT_TEMPLATE,
        url,
    ]
    print(f"🚀 Downloading with format: {format_code}")
    proc = subprocess.run(cmd)
    return proc.returncode == 0

def process_link(url: str):
    print(f"\n🔍 Processing: {url}")
    info = fetch_formats_json(url)
    if not info: return

    formats = info.get("formats") or []
    video_id, audio_id, single_id = choose_best_streams(formats)

    if video_id and audio_id:
        format_code = f"{video_id}+{audio_id}"
    elif single_id:
        format_code = single_id
    else:
        format_code = "best"

    if download_with_format(url, format_code):
        print(f"✅ Finished: {url}")
    else:
        print(f"⚠️ Failed: {url}")

def expand_links(links):
    expanded = []
    print(f"🔄 Resolving playlists and channels...")
    for link in links:
        cmd = ["yt-dlp", "--flat-playlist", "--print", "url", link]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            urls = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            if urls:
                if len(urls) > 1:
                    print(f"📑 Expanded '{link}' into {len(urls)} videos.")
                expanded.extend(urls)
            else:
                expanded.append(link)
        else:
            # If yt-dlp fails to extract flat playlist, we keep the original link and let process_link handle it
            expanded.append(link)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_expanded = []
    for u in expanded:
        if u not in seen:
            seen.add(u)
            unique_expanded.append(u)
            
    return unique_expanded

def main():
    check_ffmpeg()
    links = read_links(LINK_FILE)
    if not links:
        print("💡 Add YouTube links to 'link.txt' and run again.")
        return

    links = expand_links(links)
    print(f"📂 Videos will be saved to: {DOWNLOAD_DIR.absolute()}")
    for idx, link in enumerate(links, start=1):
        print(f"\n--- Video {idx}/{len(links)} ---")
        process_link(link)
    print("\n✨ All tasks complete.")

if __name__ == "__main__":
    main()
