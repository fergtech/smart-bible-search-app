"""
Parse LXX text_accented.csv into verse-level JSON chunks.
The CSV has word IDs but no verse markers - we need to find verse boundaries from Open Scriptures data.
"""

import json
import csv
from pathlib import Path

def download_ossp_verse_data():
    """Download verse mapping from Open Scriptures Septuagint Project"""
    import urllib.request
    
    # Try to get the word-to-verse mapping file
    url = "https://raw.githubusercontent.com/openscriptures/GreekResources/master/Septuagint/LXX-Swete/01-data/LXX.Swete.txt"
    
    print(f"Downloading verse mapping data from Open Scriptures...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            return content
    except Exception as e:
        print(f"Failed to download: {e}")
        return None

def parse_lxx_words_to_verses():
    """
    Parse text_accented.csv and group words into verses.
    Since we don't have verse boundaries in the CSV, we'll need to find another approach.
    """
    
    lxx_file = Path("lxx_data/text_accented.csv")
    
    if not lxx_file.exists():
        print(f"Error: {lxx_file} not found")
        return []
    
    print(f"Reading {lxx_file}...")
    print("Note: This CSV contains only word IDs and Greek text - no verse markers")
    print("Attempting to download verse mapping data...")
    
    # Try multiple sources for verse-mapped LXX data
    verse_data = download_ossp_verse_data()
    
    if not verse_data:
        print("\nAlternative: Checking GitHub repo for pre-formatted files...")
        print("The LXX repo has an '11_end-users_files' folder with formatted data")
        print("Let's try downloading from there...")
        
        # Try the formatted file for end users
        urls_to_try = [
            "https://raw.githubusercontent.com/eliranwong/LXX-Rahlfs-1935/main/11_end-users_files/LXX_text_only.txt",
            "https://raw.githubusercontent.com/eliranwong/LXX-Rahlfs-1935/main/11_end-users_files/MyBible/LXX_Rahlfs_1935.SQLite3",
        ]
        
        for url in urls_to_try:
            print(f"\nTrying: {url}")
            try:
                import urllib.request
                with urllib.request.urlopen(url) as response:
                    if url.endswith('.txt'):
                        content = response.read().decode('utf-8')
                        print(f"Success! Downloaded {len(content)} bytes")
                        print("First 500 characters:")
                        print(content[:500])
                        
                        # Save it
                        output_file = Path("lxx_data") / Path(url).name
                        output_file.write_text(content, encoding='utf-8')
                        print(f"\nSaved to: {output_file}")
                        return [{"status": "downloaded", "file": str(output_file)}]
                    else:
                        # Binary file (SQLite)
                        content = response.read()
                        output_file = Path("lxx_data") / Path(url).name
                        output_file.write_bytes(content)
                        print(f"Downloaded binary file: {len(content)} bytes")
                        print(f"Saved to: {output_file}")
                        return [{"status": "downloaded", "file": str(output_file)}]
            except Exception as e:
                print(f"Failed: {e}")
                continue
        
        print("\nCouldn't find pre-formatted verse data")
        print("The text_accented.csv needs to be matched with verse boundaries from another source")
        return []

if __name__ == "__main__":
    result = parse_lxx_words_to_verses()
    if result:
        print(f"\nDownloaded {len(result)} files")
    else:
        print("\nNo files downloaded - need to find proper verse-mapped LXX source")
