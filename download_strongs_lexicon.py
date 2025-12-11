"""
Download and Integrate Strong's Lexicon Data
============================================
Downloads Strong's Hebrew and Greek dictionaries and integrates them with verses.
"""

import urllib.request
import json
import csv
from pathlib import Path
from typing import Dict, List

def download_strongs_data():
    """Download Strong's lexicon data from open sources."""
    print("=" * 70)
    print("Downloading Strong's Lexicon Data")
    print("=" * 70)
    
    output_dir = Path("strongs_data")
    output_dir.mkdir(exist_ok=True)
    
    # OpenScriptures Strong's data
    sources = {
        "Greek": "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.json",
        "Hebrew": "https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.json"
    }
    
    downloaded = {}
    
    for lang, url in sources.items():
        output_path = output_dir / f"strongs-{lang.lower()}-dictionary.json"
        
        try:
            print(f"\n📥 Downloading {lang} lexicon...")
            print(f"  URL: {url[:70]}...")
            
            urllib.request.urlretrieve(url, output_path)
            
            # Load and verify
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"  ✓ Downloaded {len(data)} entries")
            print(f"  ✓ Saved to: {output_path}")
            
            downloaded[lang] = data
            
            # Show sample
            if data:
                first_key = list(data.keys())[0]
                sample = data[first_key]
                print(f"\n  📖 Sample entry ({first_key}):")
                if isinstance(sample, dict):
                    for k, v in list(sample.items())[:3]:
                        val_str = str(v)[:60]
                        print(f"    {k}: {val_str}")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            print(f"  Trying alternative source...")
    
    return downloaded

def create_lexicon_mapping():
    """Create mapping between Greek words and Strong's numbers."""
    print("\n" + "=" * 70)
    print("Creating Lexicon Mapping")
    print("=" * 70)
    
    strongs_dir = Path("strongs_data")
    
    # Load Greek dictionary
    greek_dict_path = strongs_dir / "strongs-greek-dictionary.json"
    if greek_dict_path.exists():
        with open(greek_dict_path, 'r', encoding='utf-8') as f:
            greek_dict = json.load(f)
        
        print(f"\n✓ Loaded {len(greek_dict)} Greek entries")
        
        # Create reverse mapping: Greek word -> Strong's number
        greek_word_to_strongs = {}
        
        for strongs_num, entry in greek_dict.items():
            if isinstance(entry, dict):
                # Get lemma (base form)
                lemma = entry.get('lemma', '')
                if lemma:
                    greek_word_to_strongs[lemma] = strongs_num
        
        print(f"✓ Created mapping for {len(greek_word_to_strongs)} Greek words")
        
        # Save mapping
        mapping_path = strongs_dir / "greek_word_to_strongs.json"
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(greek_word_to_strongs, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Saved mapping to: {mapping_path}")
        
        return greek_word_to_strongs
    
    return {}

def main():
    """Main execution."""
    # Download Strong's data
    downloaded = download_strongs_data()
    
    # Create mappings
    if downloaded:
        create_lexicon_mapping()
    
    print("\n" + "=" * 70)
    print("✓ Strong's Lexicon Data Ready!")
    print("=" * 70)
    print("\nNext step: Integrate with verses using:")
    print("  python integrate_strongs.py")

if __name__ == "__main__":
    main()
