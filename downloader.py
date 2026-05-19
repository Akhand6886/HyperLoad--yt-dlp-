#!/usr/bin/env python3
"""
Batch downloader using yt-dlp.

Steps implemented:
1. Read links from `link.txt` (one URL per line).
2. For each link:
   - Show available formats table (like `yt-dlp -F`).
   - Pick the best video-only stream (highest resolution, prefer avc1 > vp9 > av01).
   - Pick the best audio-only stream (highest bitrate, prefer opus > m4a).
   - Download and merge via ffmpeg into mp4.
3. Save downloaded files into a 'YouTube_Downloads' folder.
"""

import subprocess
import sys
import json
import shutil
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
LINK_FILE    = Path("link.txt")
DOWNLOAD_DIR = Path("YouTube_Downloads")
OUTPUT_TEMPLATE = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

# Video codec preference order (higher index = lower priority)
VIDEO_CODEC_PRIORITY = {"avc1": 3, "vp9": 2, "av01": 1}
# Audio codec preference order
AUDIO_CODEC_PRIORITY = {"opus": 3, "mp4a": 2, "vorbis": 1}

# ── Helpers ───────────────────────────────────────────────────────────────────

def check_ffmpeg():
    path = shutil.which("ffmpeg")
    if path:
        print(f"✅ ffmpeg found: {path}")
        return True
    print("⚠️  ffmpeg not found — merging will fail!")
    print("   Install: brew install ffmpeg")
    return False


def read_links(file_path: Path):
    if not file_path.exists():
        file_path.touch()
        print(f"📝 Created {file_path}. Add URLs and run again.")
        return []
    with file_path.open("r", encoding="utf-8") as f:
        lines = [line.split("#", 1)[0].strip() for line in f]
    return [l for l in lines if l]


def ytdlp(*args, capture=True):
    """Run yt-dlp with common flags, return CompletedProcess."""
    cmd = ["yt-dlp", "--no-check-certificate"] + list(args)
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)


# ── Format table ──────────────────────────────────────────────────────────────

def show_format_table(url: str):
    """Print the full yt-dlp -F table, filtering out storyboard/mhtml rows."""
    print("\n📋 Available formats:")
    proc = ytdlp("-F", url, capture=False)   # streams directly to stdout
    return proc.returncode == 0


# ── Format selection ──────────────────────────────────────────────────────────

def _codec_family(codec: str | None, priority_map: dict) -> int:
    if not codec or codec == "none":
        return 0
    for key, score in priority_map.items():
        if key in codec.lower():
            return score
    return 1  # unknown but valid


def choose_best_streams(formats: list):
    """
    Return (video_fmt_id, audio_fmt_id, chosen_label).

    Selection logic:
      Video → highest height, then highest VBR, then prefer avc1 > vp9 > av01.
      Audio → highest ABR/TBR, then prefer opus > mp4a.
    """
    video_candidates = []
    audio_candidates = []
    combined_candidates = []

    for f in formats:
        fmt_id  = str(f.get("format_id", ""))
        vcodec  = f.get("vcodec") or "none"
        acodec  = f.get("acodec") or "none"
        ext     = f.get("ext", "")

        # Skip storyboard / mhtml thumbnails
        if ext == "mhtml" or f.get("format_note", "") == "storyboard":
            continue

        has_video = vcodec != "none"
        has_audio = acodec != "none"

        if has_video and not has_audio:
            height    = f.get("height") or 0
            vbr       = f.get("vbr") or f.get("tbr") or 0
            v_pref    = _codec_family(vcodec, VIDEO_CODEC_PRIORITY)
            video_candidates.append((height, vbr, v_pref, fmt_id))

        elif has_audio and not has_video:
            abr       = f.get("abr") or f.get("tbr") or 0
            a_pref    = _codec_family(acodec, AUDIO_CODEC_PRIORITY)
            audio_candidates.append((abr, a_pref, fmt_id))

        elif has_video and has_audio:
            height    = f.get("height") or 0
            vbr       = f.get("vbr") or f.get("tbr") or 0
            combined_candidates.append((height, vbr, fmt_id))

    video_candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    audio_candidates.sort(key=lambda x: (x[0], x[1]))
    combined_candidates.sort(key=lambda x: (x[0], x[1]))

    if video_candidates and audio_candidates:
        best_video = video_candidates[-1]
        best_audio = audio_candidates[-1]
        v_id = best_video[3]
        a_id = best_audio[2]
        label = (
            f"Video → ID {v_id} "
            f"({best_video[0]}p, {best_video[1]:.0f}kbps)  "
            f"Audio → ID {a_id} "
            f"({best_audio[0]:.0f}kbps)"
        )
        return v_id, a_id, label

    if combined_candidates:
        best = combined_candidates[-1]
        label = f"Combined → ID {best[2]} ({best[0]}p, {best[1]:.0f}kbps)"
        return None, None, f"combined:{best[2]}"

    return None, None, "best (fallback)"


def fetch_formats_json(url: str):
    proc = ytdlp("--dump-json", url)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        print(f"❌ yt-dlp failed to fetch info for {url}")
        # Surface the most relevant error line
        for line in reversed(stderr.splitlines()):
            if line.startswith("ERROR"):
                print(f"   {line}")
                break
        return None

    output = proc.stdout.strip()
    if not output:
        print(f"⚠️  No output returned for {url}")
        return None

    try:
        lines = output.splitlines()
        if len(lines) > 1:
            print(f"ℹ️  Multiple items detected — processing first entry.")
            return json.loads(lines[0])
        return json.loads(output)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None


# ── Download ──────────────────────────────────────────────────────────────────

def download(url: str, format_code: str):
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    args = [
        "-f", format_code,
        "--merge-output-format", "mp4",
        "-o", OUTPUT_TEMPLATE,
        "--progress",
        url,
    ]
    print(f"🚀 Starting download…")
    proc = ytdlp(*args, capture=False)
    return proc.returncode == 0


# ── Per-link orchestration ────────────────────────────────────────────────────

def process_link(url: str):
    print(f"\n🔍 Processing: {url}")

    # 1. Show format table (streams to terminal just like yt-dlp -F)
    show_format_table(url)

    # 2. Fetch structured JSON for smart selection
    info = fetch_formats_json(url)
    if not info:
        return

    title   = info.get("title", url)
    formats = info.get("formats") or []

    print(f"\n🎬 Title : {title}")

    video_id, audio_id, label = choose_best_streams(formats)

    if video_id and audio_id:
        format_code = f"{video_id}+{audio_id}"
    elif label.startswith("combined:"):
        format_code = label.split(":", 1)[1]
        label = f"Combined stream {format_code}"
    else:
        format_code = "bestvideo+bestaudio/best"
        label = "best (fallback)"

    print(f"✨ Selected: {label}")
    print(f"   Format code: {format_code}")

    if download(url, format_code):
        print(f"✅ Finished: {title}")
    else:
        print(f"⚠️  Download failed for: {url}")


# ── Playlist / channel expansion ──────────────────────────────────────────────

def expand_links(links: list) -> list:
    expanded = []
    print("🔄 Resolving playlists and channels…")
    for link in links:
        proc = ytdlp(
            "--flat-playlist", "--print", "url",
            "--ignore-errors", link
        )
        urls = [
            line.strip() for line in proc.stdout.splitlines()
            if line.strip() and line.strip() != "NA"
        ]
        if urls:
            if len(urls) > 1:
                print(f"📑 Expanded '{link}' → {len(urls)} videos.")
            expanded.extend(urls)
        else:
            # Single video — keep original URL
            expanded.append(link)

    # Deduplicate, preserve order
    seen, unique = set(), []
    for u in expanded:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    check_ffmpeg()
    links = read_links(LINK_FILE)
    if not links:
        print("💡 Add YouTube links to 'link.txt' and run again.")
        return

    links = expand_links(links)
    print(f"📂 Saving to: {DOWNLOAD_DIR.absolute()}")

    for idx, link in enumerate(links, start=1):
        print(f"\n{'━'*60}")
        print(f"  Video {idx}/{len(links)}")
        print(f"{'━'*60}")
        process_link(link)

    print("\n✨ All tasks complete.")


if __name__ == "__main__":
    main()
