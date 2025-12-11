"""
GitHub Text Downloader
======================
Downloads biblical text files from the GitHub repositories listed in the URL files.

Repositories:
- LXX (Septuagint): https://github.com/eliranwong/LXX-Rahlfs-1935
- SBLGNT: https://github.com/Faithlife/SBLGNT
"""

import urllib.request
import json
import os
from pathlib import Path

def download_lxx_texts():
    """Download Septuagint text files from GitHub."""
    print("Downloading LXX (Septuagint) texts...")
    
    # LXX repository structure - these are example paths
    # You would need to explore the actual repository structure
    base_url = "https://raw.githubusercontent.com/eliranwong/LXX-Rahlfs-1935/main/"
    
    # Example files to download (adjust based on actual repository structure)
    files_to_download = [
        "Genesis.txt",
        "Exodus.txt",
        # Add more books as needed
    ]
    
    output_dir = Path("lxx_texts")
    output_dir.mkdir(exist_ok=True)
    
    for filename in files_to_download:
        try:
            url = base_url + filename
            output_path = output_dir / filename
            print(f"  Downloading {filename}...")
            urllib.request.urlretrieve(url, output_path)
            print(f"    ✓ Saved to {output_path}")
        except Exception as e:
            print(f"    ✗ Error downloading {filename}: {e}")

def download_sblgnt_texts():
    """Download SBLGNT text files from GitHub."""
    print("\nDownloading SBLGNT (Greek NT) texts...")
    
    base_url = "https://raw.githubusercontent.com/Faithlife/SBLGNT/master/data/sblgnt/text/"
    
    # NT books
    books = [
        "Matthew.txt",
        "Mark.txt", 
        "Luke.txt",
        "John.txt",
        # Add more books as needed
    ]
    
    output_dir = Path("sblgnt_texts")
    output_dir.mkdir(exist_ok=True)
    
    for filename in books:
        try:
            url = base_url + filename
            output_path = output_dir / filename
            print(f"  Downloading {filename}...")
            urllib.request.urlretrieve(url, output_path)
            print(f"    ✓ Saved to {output_path}")
        except Exception as e:
            print(f"    ✗ Error downloading {filename}: {e}")

def main():
    print("=" * 70)
    print("GitHub Biblical Texts Downloader")
    print("=" * 70)
    print("\nNOTE: This script contains example URLs.")
    print("Please explore the actual GitHub repositories to find the correct file paths:")
    print("  - LXX: https://github.com/eliranwong/LXX-Rahlfs-1935")
    print("  - SBLGNT: https://github.com/Faithlife/SBLGNT")
    print("\nYou may need to manually download files or adjust the URLs in this script.")
    print("=" * 70)
    
    # Uncomment to run downloads
    # download_lxx_texts()
    # download_sblgnt_texts()
    
    print("\n✓ Complete!")
    print("\nManual alternative:")
    print("1. Visit the GitHub repositories")
    print("2. Download the text files you need")
    print("3. Place them in the book-intel directory")
    print("4. Re-run preprocess_biblical_texts.py")

if __name__ == "__main__":
    main()
