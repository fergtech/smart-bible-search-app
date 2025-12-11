"""
Download Structured Biblical Data
==================================
Downloads verse-level structured data from GitHub repositories.
"""

import urllib.request
import json
import os
from pathlib import Path
import zipfile
import io

def download_file(url, output_path):
    """Download a file from URL to output path."""
    try:
        print(f"    Downloading from {url[:80]}...")
        urllib.request.urlretrieve(url, output_path)
        print(f"    ✓ Saved to {output_path}")
        return True
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def download_lxx_structured_data():
    """Download LXX structured data with verse mappings."""
    print("\n📥 Downloading LXX structured data...")
    print("  Note: LXX repository doesn't have simple .txt files")
    print("  It contains structured TSV files in subdirectories")
    print("  You can manually explore: https://github.com/eliranwong/LXX-Rahlfs-1935/tree/master/11_end-users_files")
    
    # For now, we'll focus on SBLGNT which has clearer structure
    return []

def download_sblgnt_structured_data():
    """Download SBLGNT structured data with verse mappings."""
    print("\n📥 Downloading SBLGNT structured data...")
    
    base_url = "https://raw.githubusercontent.com/Faithlife/SBLGNT/master/"
    
    output_dir = Path("sblgnt_data")
    output_dir.mkdir(exist_ok=True)
    
    # SBLGNT text files - correct paths from repository
    files_to_download = [
        "data/sblgnt/text/Matt.txt",
        "data/sblgnt/text/Mark.txt",
        "data/sblgnt/text/Luke.txt",
        "data/sblgnt/text/John.txt",
        "data/sblgnt/text/Acts.txt",
        "data/sblgnt/text/Rom.txt",
        "data/sblgnt/text/1Cor.txt",
        "data/sblgnt/text/2Cor.txt",
        "data/sblgnt/text/Gal.txt",
        "data/sblgnt/text/Eph.txt",
        "data/sblgnt/text/Phil.txt",
        "data/sblgnt/text/Col.txt",
        "data/sblgnt/text/1Thess.txt",
        "data/sblgnt/text/2Thess.txt",
        "data/sblgnt/text/1Tim.txt",
        "data/sblgnt/text/2Tim.txt",
        "data/sblgnt/text/Titus.txt",
        "data/sblgnt/text/Phlm.txt",
        "data/sblgnt/text/Heb.txt",
        "data/sblgnt/text/Jas.txt",
        "data/sblgnt/text/1Pet.txt",
        "data/sblgnt/text/2Pet.txt",
        "data/sblgnt/text/1John.txt",
        "data/sblgnt/text/2John.txt",
        "data/sblgnt/text/3John.txt",
        "data/sblgnt/text/Jude.txt",
        "data/sblgnt/text/Rev.txt",
    ]
    
    downloaded_files = []
    
    for file_path in files_to_download:
        url = base_url + file_path
        filename = Path(file_path).name
        output_path = output_dir / filename
        
        if download_file(url, output_path):
            downloaded_files.append(output_path)
    
    return downloaded_files

def explore_downloaded_file(file_path):
    """Show sample content from downloaded file."""
    print(f"\n📄 Sample from {file_path.name}:")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:10]):  # First 10 lines
                print(f"  {i+1}: {line.rstrip()[:100]}")
        print(f"  ... (total {len(lines)} lines)")
    except Exception as e:
        print(f"  Error reading file: {e}")

def main():
    print("=" * 70)
    print("Download Structured Biblical Data")
    print("=" * 70)
    
    # Download LXX data
    lxx_files = download_lxx_structured_data()
    
    # Download SBLGNT data
    sblgnt_files = download_sblgnt_structured_data()
    
    print("\n" + "=" * 70)
    print(f"✓ Downloaded {len(lxx_files)} LXX files and {len(sblgnt_files)} SBLGNT files")
    print("=" * 70)
    
    # Show samples
    if lxx_files:
        explore_downloaded_file(lxx_files[0])
    
    if sblgnt_files:
        explore_downloaded_file(sblgnt_files[0])
    
    print("\n" + "=" * 70)
    print("Next steps:")
    print("1. Review the downloaded files in lxx_data/ and sblgnt_data/")
    print("2. Parse these files to extract verse-level data")
    print("3. Map PDF content to correct book/chapter/verse")

if __name__ == "__main__":
    main()
