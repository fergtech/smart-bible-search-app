"""
GitHub Repository Explorer
==========================
Explores the structure of biblical text repositories to find verse mapping files.
"""

import urllib.request
import json
from pathlib import Path

def explore_lxx_repository():
    """Explore LXX repository structure."""
    print("Exploring LXX-Rahlfs-1935 repository...")
    
    # GitHub API endpoint for repository contents
    api_url = "https://api.github.com/repos/eliranwong/LXX-Rahlfs-1935/contents"
    
    try:
        with urllib.request.urlopen(api_url) as response:
            contents = json.loads(response.read().decode())
        
        print("\n📁 Repository structure:")
        for item in contents:
            print(f"  {'📁' if item['type'] == 'dir' else '📄'} {item['name']}")
            if item['name'].endswith(('.txt', '.json', '.xml', '.csv')):
                print(f"      → {item['download_url'][:80]}...")
        
        return contents
    except Exception as e:
        print(f"  Error: {e}")
        return []

def explore_sblgnt_repository():
    """Explore SBLGNT repository structure."""
    print("\n\nExploring SBLGNT repository...")
    
    api_url = "https://api.github.com/repos/Faithlife/SBLGNT/contents"
    
    try:
        with urllib.request.urlopen(api_url) as response:
            contents = json.loads(response.read().decode())
        
        print("\n📁 Repository structure:")
        for item in contents:
            print(f"  {'📁' if item['type'] == 'dir' else '📄'} {item['name']}")
            
            # Explore subdirectories
            if item['type'] == 'dir' and item['name'] in ['data', 'text', 'sblgnt']:
                print(f"    Exploring {item['name']}/...")
                try:
                    with urllib.request.urlopen(item['url']) as sub_response:
                        sub_contents = json.loads(sub_response.read().decode())
                        for sub_item in sub_contents[:10]:  # Limit output
                            print(f"      {'📁' if sub_item['type'] == 'dir' else '📄'} {sub_item['name']}")
                except:
                    pass
        
        return contents
    except Exception as e:
        print(f"  Error: {e}")
        return []

def main():
    print("=" * 70)
    print("Biblical Text Repository Explorer")
    print("=" * 70)
    
    lxx_contents = explore_lxx_repository()
    sblgnt_contents = explore_sblgnt_repository()
    
    print("\n" + "=" * 70)
    print("✓ Exploration complete!")
    print("\nNext steps:")
    print("1. Review the repository structure above")
    print("2. Identify verse mapping files (.txt, .json, .xml)")
    print("3. Update the preprocessing script with correct file paths")

if __name__ == "__main__":
    main()
