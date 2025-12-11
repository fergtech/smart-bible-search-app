"""
Download Complete Strong's Lexicon Data
========================================
Downloads comprehensive Strong's Hebrew and Greek lexicons.
"""

import urllib.request
import urllib.parse
from pathlib import Path

def download_strongs():
    """Download Strong's lexicon files."""
    print("=" * 70)
    print("Downloading Strong's Lexicon Data")
    print("=" * 70)
    
    output_dir = Path("strongs_data")
    output_dir.mkdir(exist_ok=True)
    
    # STEPBible Strong's data (properly encoded URLs)
    files = {
        "Greek": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt",
        "Hebrew": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/TBESH%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Hebrew%20-%20STEPBible.org%20CC%20BY.txt"
    }
    
    downloaded = []
    
    for lang, url in files.items():
        output_filename = f"strongs_{lang.lower()}_lexicon.txt"
        output_path = output_dir / output_filename
        
        print(f"\nDownloading {lang} lexicon...")
        print(f"  File: {output_filename}")
        
        try:
            urllib.request.urlretrieve(url, output_path)
            size_kb = output_path.stat().st_size / 1024
            print(f"  Size: {size_kb:.1f} KB")
            print(f"  Status: SUCCESS")
            
            # Show sample
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:5]
                print(f"  Sample lines:")
                for i, line in enumerate(lines, 1):
                    print(f"    {i}. {line.rstrip()[:70]}")
            
            downloaded.append(output_filename)
        
        except Exception as e:
            print(f"  Status: FAILED")
            print(f"  Error: {str(e)[:100]}")
    
    print("\n" + "=" * 70)
    print(f"Downloaded {len(downloaded)} lexicon files:")
    for f in downloaded:
        print(f"  - {f}")
    print("=" * 70)
    
    return len(downloaded)

if __name__ == "__main__":
    count = download_strongs()
    if count > 0:
        print("\nStrong's lexicon data is ready!")
        print("Next: python create_final_integrated_dataset.py")
    else:
        print("\nFailed to download Strong's data")
        print("Using embedded sample lexicon instead")
