# YouTube Batch Downloader

A simple, high-quality batch downloader for YouTube and other supported sites using `yt-dlp` and `ffmpeg`.

## 🚀 Features
- **Batch Processing**: Download multiple videos at once from a text file.
- **Maximum Quality**: Automatically selects the best video and audio streams and merges them.
- **Dedicated Storage**: Saves all downloads into a `downloads/` folder.
- **Error Handling**: Skips failed downloads and continues with the rest of the list.

## 🛠️ Setup

### 1. Install Dependencies
Ensure you have Python 3 installed, then install `yt-dlp`:
```bash
pip install yt-dlp
```

You also need `ffmpeg` for merging video and audio streams:
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 2. Prepare Links
Open `link.txt` and add the URLs you want to download (one per line). Lines starting with `#` are ignored.

## 📂 Usage
Run the downloader using the provided script:
```bash
python3 downloader.py
```
Or use the convenience script:
```bash
./run.sh
```

All downloaded videos will be stored in the `downloads/` directory.

## 📄 Files
- `downloader.py`: The main Python script.
- `link.txt`: Your list of URLs.
- `downloads/`: Where your videos will be saved.
- `run.sh`: Shortcut to run the downloader.
