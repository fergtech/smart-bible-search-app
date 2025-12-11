"""
Create lexicon_metadata.json from Greek/Hebrew lexicon CSVs
Format: {word: {definition, transliteration, strongs_number, semantic_domain}}
"""

import json
import csv
from pathlib import Path

def parse_lxx_lexicon():
    """Parse LXX Greek lexicon CSV"""
    
    lexicon_file = Path("lxx_data/LXX_lexicon_formatted_for_UniqueBibleAppPlus.csv")
    
    if not lexicon_file.exists():
        print(f"Warning: {lexicon_file} not found")
        return {}
    
    print(f"Parsing {lexicon_file.name}...")
    
    lexicon = {}
    
    with lexicon_file.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 1000 == 0:
                print(f"  Processed {line_num:,} entries...")
            
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                strongs = parts[0]  # L700001
                greek_word = parts[1]  # Greek text
                transliteration = parts[2]  # Romanized
                pos = parts[3]  # Part of speech
                gloss = parts[4]  # English definition
                
                # Clean HTML from definition
                import re
                gloss_clean = re.sub(r'<[^>]+>', '', gloss)
                gloss_clean = re.sub(r'\s+', ' ', gloss_clean).strip()
                
                lexicon[greek_word] = {
                    "language": "Greek",
                    "transliteration": transliteration,
                    "part_of_speech": pos,
                    "definition": gloss_clean[:200],  # Limit length
                    "strongs_number": strongs,
                    "source": "LXX-Rahlfs-1935"
                }
    
    print(f"  Loaded {len(lexicon):,} Greek words")
    return lexicon

def create_lexicon_metadata():
    """Create combined lexicon metadata file"""
    
    print("=" * 60)
    print("Lexicon Metadata Generation")
    print("=" * 60)
    
    # Parse Greek lexicon
    print("\nParsing Greek lexicon...")
    greek_lexicon = parse_lxx_lexicon()
    
    # Combine all lexicons
    combined_lexicon = {}
    combined_lexicon.update(greek_lexicon)
    
    # Save
    output_file = Path("lexicon_metadata.json")
    
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(combined_lexicon, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ Lexicon metadata created")
    print(f"✓ Output: {output_file}")
    print(f"✓ Total entries: {len(combined_lexicon):,}")
    print(f"✓ File size: {output_file.stat().st_size / 1024:.1f} KB")
    print("=" * 60)
    
    # Show samples
    print("\nSample entries:")
    for i, (word, data) in enumerate(list(combined_lexicon.items())[:3]):
        print(f"\n{i+1}. {word} ({data['transliteration']})")
        print(f"   {data['part_of_speech']}")
        print(f"   {data['definition']}")

if __name__ == "__main__":
    create_lexicon_metadata()
