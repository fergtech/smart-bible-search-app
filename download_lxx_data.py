"""
Download LXX Greek Old Testament Data
======================================
Downloads structured Septuagint data from the LXX-Rahlfs-1935 repository.
"""

import urllib.request
import json
from pathlib import Path

def download_lxx_structured_files():
    """Download LXX data files from the 11_end-users_files directory."""
    print("=" * 70)
    print("Downloading LXX (Greek Old Testament) Data")
    print("=" * 70)
    
    output_dir = Path("lxx_data")
    output_dir.mkdir(exist_ok=True)
    
    base_url = "https://raw.githubusercontent.com/eliranwong/LXX-Rahlfs-1935/master/11_end-users_files/"
    
    # Key files from the repository
    files = [
        "LXX-Rahlfs-1935.txt",
        "README.md"
    ]
    
    # First, let's check what files actually exist
    print("\nChecking repository structure...")
    
    try:
        api_url = "https://api.github.com/repos/eliranwong/LXX-Rahlfs-1935/contents/11_end-users_files"
        response = urllib.request.urlopen(api_url)
        contents = json.loads(response.read().decode())
        
        print(f"\nFound {len(contents)} items in 11_end-users_files/")
        
        downloaded = 0
        for item in contents:
            if item['type'] == 'file':
                filename = item['name']
                download_url = item['download_url']
                output_path = output_dir / filename
                
                print(f"\nDownloading: {filename}")
                print(f"  Size: {item['size'] / 1024:.1f} KB")
                
                try:
                    urllib.request.urlretrieve(download_url, output_path)
                    print(f"  Status: SUCCESS")
                    downloaded += 1
                    
                    # Show preview for text files
                    if filename.endswith('.txt'):
                        with open(output_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()[:5]
                            print(f"  Preview:")
                            for line in lines:
                                print(f"    {line.rstrip()[:80]}")
                
                except Exception as e:
                    print(f"  Status: FAILED - {e}")
        
        print(f"\n{'=' * 70}")
        print(f"Downloaded {downloaded} files to {output_dir}/")
        print(f"{'=' * 70}")
        
        return downloaded
        
    except Exception as e:
        print(f"Error accessing repository: {e}")
        return 0

def main():
    downloaded = download_lxx_structured_files()
    
    if downloaded > 0:
        print("\nNext step: Parse LXX files")
        print("  python parse_lxx_data.py")
    else:
        print("\nNo files downloaded. Check repository structure.")

if __name__ == "__main__":
    main()
