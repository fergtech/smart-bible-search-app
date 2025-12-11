"""
Integrate Strong's Lexicon with Biblical Verses
===============================================
Adds Strong's numbers, root words, and semantic domains to verses.
"""

import json
from pathlib import Path
from typing import Dict, List
import re

# Sample Strong's lexicon data (top words from NT)
SAMPLE_STRONGS_GREEK = {
    "λόγος": {
        "strongs": "G3056",
        "transliteration": "logos",
        "definition": "word, speech, divine expression, reason",
        "semantic_domains": ["communication", "divine revelation", "reason"]
    },
    "θεός": {
        "strongs": "G2316",
        "transliteration": "theos",
        "definition": "God, deity",
        "semantic_domains": ["deity", "divine beings", "theology"]
    },
    "Χριστός": {
        "strongs": "G5547",
        "transliteration": "Christos",
        "definition": "Christ, Messiah, Anointed One",
        "semantic_domains": ["messianic titles", "jesus christ", "anointing"]
    },
    "Ἰησοῦς": {
        "strongs": "G2424",
        "transliteration": "Iēsous",
        "definition": "Jesus",
        "semantic_domains": ["personal names", "jesus christ", "salvation"]
    },
    "πίστις": {
        "strongs": "G4102",
        "transliteration": "pistis",
        "definition": "faith, belief, trust, confidence",
        "semantic_domains": ["faith", "belief systems", "trust"]
    },
    "ἀγάπη": {
        "strongs": "G26",
        "transliteration": "agapē",
        "definition": "love, divine love, charity",
        "semantic_domains": ["love", "emotions", "divine attributes"]
    },
    "κύριος": {
        "strongs": "G2962",
        "transliteration": "kyrios",
        "definition": "Lord, master, owner",
        "semantic_domains": ["authority", "divine titles", "ownership"]
    },
    "πνεῦμα": {
        "strongs": "G4151",
        "transliteration": "pneuma",
        "definition": "spirit, Spirit, breath, wind",
        "semantic_domains": ["holy spirit", "spiritual beings", "breath"]
    },
    "ἁμαρτία": {
        "strongs": "G266",
        "transliteration": "hamartia",
        "definition": "sin, missing the mark, transgression",
        "semantic_domains": ["sin", "moral failing", "transgression"]
    },
    "υἱός": {
        "strongs": "G5207",
        "transliteration": "huios",
        "definition": "son, descendant",
        "semantic_domains": ["family relationships", "sonship", "kinship"]
    },
    "ἐκκλησία": {
        "strongs": "G1577",
        "transliteration": "ekklēsia",
        "definition": "church, assembly, congregation",
        "semantic_domains": ["church", "assembly", "community"]
    },
    "χάρις": {
        "strongs": "G5485",
        "transliteration": "charis",
        "definition": "grace, favor, kindness",
        "semantic_domains": ["grace", "divine favor", "kindness"]
    },
    "εἰρήνη": {
        "strongs": "G1515",
        "transliteration": "eirēnē",
        "definition": "peace, harmony, rest",
        "semantic_domains": ["peace", "tranquility", "reconciliation"]
    },
    "δόξα": {
        "strongs": "G1391",
        "transliteration": "doxa",
        "definition": "glory, honor, praise, splendor",
        "semantic_domains": ["glory", "honor", "divine presence"]
    },
    "ἀλήθεια": {
        "strongs": "G225",
        "transliteration": "alētheia",
        "definition": "truth, reality, sincerity",
        "semantic_domains": ["truth", "reality", "honesty"]
    },
    "ζωή": {
        "strongs": "G2222",
        "transliteration": "zōē",
        "definition": "life, eternal life",
        "semantic_domains": ["life", "eternal life", "vitality"]
    },
    "βασιλεία": {
        "strongs": "G932",
        "transliteration": "basileia",
        "definition": "kingdom, reign, royal power",
        "semantic_domains": ["kingdom", "authority", "reign"]
    },
    "εὐαγγέλιον": {
        "strongs": "G2098",
        "transliteration": "euangelion",
        "definition": "gospel, good news",
        "semantic_domains": ["gospel", "good news", "message"]
    },
    "δικαιοσύνη": {
        "strongs": "G1343",
        "transliteration": "dikaiosynē",
        "definition": "righteousness, justice",
        "semantic_domains": ["righteousness", "justice", "moral integrity"]
    },
    "σωτηρία": {
        "strongs": "G4991",
        "transliteration": "sōtēria",
        "definition": "salvation, deliverance, preservation",
        "semantic_domains": ["salvation", "deliverance", "rescue"]
    }
}

def load_verses(file_path: str) -> List[Dict]:
    """Load verses from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_greek_words_in_verse(verse_text: str) -> List[str]:
    """Extract Greek words from verse text."""
    # Split on whitespace and punctuation
    words = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]+', verse_text)
    return words

def add_lexicon_data(verse: Dict, lexicon: Dict) -> Dict:
    """Add Strong's lexicon data to a verse."""
    if verse['language'] != 'Greek':
        return verse
    
    text = verse['text']
    words = find_greek_words_in_verse(text)
    
    # Find matching words in lexicon
    lexicon_entries = []
    
    for word in words:
        # Try exact match
        if word in lexicon:
            lexicon_entries.append(lexicon[word])
        # Try lowercase
        elif word.lower() in lexicon:
            lexicon_entries.append(lexicon[word.lower()])
    
    # Add the most significant lexicon entry (if any)
    if lexicon_entries:
        # Use the first match for now
        verse['lexicon'] = lexicon_entries[0]
        verse['word_count'] = len(words)
        verse['lexicon_matches'] = len(lexicon_entries)
    
    return verse

def integrate_strongs():
    """Main integration function."""
    print("=" * 70)
    print("Integrating Strong's Lexicon with Verses")
    print("=" * 70)
    
    # Load enhanced verses
    verses_path = Path("biblical_verses_enhanced.json")
    
    if not verses_path.exists():
        print(f"Error: {verses_path} not found!")
        print("Run: python preprocess_enhanced.py first")
        return
    
    print(f"\n📖 Loading verses from {verses_path}...")
    verses = load_verses(str(verses_path))
    print(f"✓ Loaded {len(verses)} verses")
    
    # Add lexicon data
    print(f"\n🔍 Adding Strong's lexicon data...")
    print(f"   Using {len(SAMPLE_STRONGS_GREEK)} Greek word entries")
    
    enriched_verses = []
    verses_with_lexicon = 0
    
    for verse in verses:
        enriched = add_lexicon_data(verse, SAMPLE_STRONGS_GREEK)
        enriched_verses.append(enriched)
        
        if 'lexicon' in enriched:
            verses_with_lexicon += 1
    
    print(f"✓ Added lexicon data to {verses_with_lexicon} verses")
    
    # Save enriched verses
    output_path = "biblical_verses_with_strongs.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_verses, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved enriched verses to: {output_path}")
    
    # Show statistics
    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)
    print(f"  Total verses: {len(enriched_verses)}")
    print(f"  Verses with lexicon data: {verses_with_lexicon}")
    print(f"  Coverage: {verses_with_lexicon / len(enriched_verses) * 100:.1f}%")
    
    # Show samples
    print("\n" + "=" * 70)
    print("Sample Verses with Lexicon Data")
    print("=" * 70)
    
    count = 0
    for verse in enriched_verses:
        if 'lexicon' in verse and count < 3:
            print(f"\n📖 {verse['book']} {verse['chapter']}:{verse['verse']}")
            print(f"   Text: {verse['text'][:80]}...")
            print(f"   Strong's: {verse['lexicon']['strongs']}")
            print(f"   Root: {verse['lexicon']['transliteration']}")
            print(f"   Definition: {verse['lexicon']['definition']}")
            print(f"   Domains: {', '.join(verse['lexicon']['semantic_domains'])}")
            count += 1
    
    print("\n" + "=" * 70)
    print("Next steps:")
    print("  1. Expand Strong's lexicon with more words")
    print("  2. Generate embeddings: python generate_embeddings.py")
    print("  3. Add cross-references")
    print("=" * 70)

if __name__ == "__main__":
    integrate_strongs()
