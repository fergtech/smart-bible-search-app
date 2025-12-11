"""
Download King James Bible from Project Gutenberg
"""
import urllib.request
from pathlib import Path

def download_kjv():
    url = "https://www.gutenberg.org/files/10/10-0.txt"
    output_file = Path("pg10.txt")
    
    print(f"Downloading KJV from Project Gutenberg...")
    print(f"URL: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            
        output_file.write_text(content, encoding='utf-8')
        
        print(f"\nSuccess! Downloaded {len(content):,} characters")
        print(f"Saved to: {output_file}")
        print(f"\nFirst 500 characters:")
        print(content[:500])
        
        return str(output_file)
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return None

if __name__ == "__main__":
    download_kjv()
