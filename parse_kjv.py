"""
Parse King James Bible (Project Gutenberg pg10.txt) into verse-level chunks.
Output: kjv_chunks.jsonl (one JSON object per line)
"""

import json
import re
from pathlib import Path

def clean_gutenberg_text(text):
    """Remove Project Gutenberg headers and footers"""
    
    # Find the start of actual Bible text
    # Typically after "*** START OF THE PROJECT GUTENBERG EBOOK" and initial TOC
    start_markers = [
        "The First Book of Moses: Called Genesis",
        "1:1 In the beginning God created"
    ]
    
    start_pos = 0
    for marker in start_markers:
        pos = text.find(marker)
        if pos > 0 and pos < 10000:  # Within reasonable header range
            start_pos = max(start_pos, pos)
    
    # Find end marker
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"
    end_pos = text.find(end_marker)
    if end_pos < 0:
        end_pos = len(text)
    
    cleaned = text[start_pos:end_pos]
    
    print(f"Cleaned text: {len(text):,} → {len(cleaned):,} characters")
    return cleaned

def extract_kjv_verses(text):
    """
    Extract verses from KJV text.
    KJV format is typically: "Book Chapter:Verse Text goes here..."
    """
    
    verses = []
    
    # Map full Gutenberg titles to short book names
    book_mappings = {
        "The First Book of Moses: Called Genesis": "Genesis",
        "The Second Book of Moses: Called Exodus": "Exodus",
        "The Third Book of Moses: Called Leviticus": "Leviticus",
        "The Fourth Book of Moses: Called Numbers": "Numbers",
        "The Fifth Book of Moses: Called Deuteronomy": "Deuteronomy",
        "The Book of Joshua": "Joshua",
        "The Book of Judges": "Judges",
        "The Book of Ruth": "Ruth",
        "The First Book of Samuel": "1 Samuel",
        "The Second Book of Samuel": "2 Samuel",
        "The First Book of the Kings": "1 Kings",
        "The Second Book of the Kings": "2 Kings",
        "The First Book of the Chronicles": "1 Chronicles",
        "The Second Book of the Chronicles": "2 Chronicles",
        "Ezra": "Ezra",
        "The Book of Nehemiah": "Nehemiah",
        "The Book of Esther": "Esther",
        "The Book of Job": "Job",
        "The Book of Psalms": "Psalms",
        "The Proverbs": "Proverbs",
        "Ecclesiastes": "Ecclesiastes",
        "The Song of Solomon": "Song of Solomon",
        "The Book of the Prophet Isaiah": "Isaiah",
        "The Book of the Prophet Jeremiah": "Jeremiah",
        "The Lamentations of Jeremiah": "Lamentations",
        "The Book of the Prophet Ezekiel": "Ezekiel",
        "The Book of Daniel": "Daniel",
        "Hosea": "Hosea",
        "Joel": "Joel",
        "Amos": "Amos",
        "Obadiah": "Obadiah",
        "Jonah": "Jonah",
        "Micah": "Micah",
        "Nahum": "Nahum",
        "Habakkuk": "Habakkuk",
        "Zephaniah": "Zephaniah",
        "Haggai": "Haggai",
        "Zechariah": "Zechariah",
        "Malachi": "Malachi",
        "The Gospel According to Saint Matthew": "Matthew",
        "The Gospel According to Saint Mark": "Mark",
        "The Gospel According to Saint Luke": "Luke",
        "The Gospel According to Saint John": "John",
        "The Acts of the Apostles": "Acts",
        "The Epistle of Paul the Apostle to the Romans": "Romans",
        "The First Epistle of Paul the Apostle to the Corinthians": "1 Corinthians",
        "The Second Epistle of Paul the Apostle to the Corinthians": "2 Corinthians",
        "The Epistle of Paul the Apostle to the Galatians": "Galatians",
        "The Epistle of Paul the Apostle to the Ephesians": "Ephesians",
        "The Epistle of Paul the Apostle to the Philippians": "Philippians",
        "The Epistle of Paul the Apostle to the Colossians": "Colossians",
        "The First Epistle of Paul the Apostle to the Thessalonians": "1 Thessalonians",
        "The Second Epistle of Paul the Apostle to the Thessalonians": "2 Thessalonians",
        "The First Epistle of Paul the Apostle to Timothy": "1 Timothy",
        "The Second Epistle of Paul the Apostle to Timothy": "2 Timothy",
        "The Epistle of Paul the Apostle to Titus": "Titus",
        "The Epistle of Paul the Apostle to Philemon": "Philemon",
        "The Epistle of Paul the Apostle to the Hebrews": "Hebrews",
        "The General Epistle of James": "James",
        "The First Epistle General of Peter": "1 Peter",
        "The Second General Epistle of Peter": "2 Peter",
        "The First Epistle General of John": "1 John",
        "The Second Epistle General of John": "2 John",
        "The Third Epistle General of John": "3 John",
        "The General Epistle of Jude": "Jude",
        "The Revelation of Saint John the Divine": "Revelation"
    }
    
    # Pattern: Chapter:Verse at start of line followed by text
    # Example: "1:1 In the beginning God created..."
    verse_pattern = re.compile(r'^(\d+):(\d+)\s+(.+?)(?=^\d+:\d+|\Z)', re.MULTILINE | re.DOTALL)
    
    # Split text into book sections
    current_book = None
    current_section = ""
    
    lines = text.split('\n')
    book_count = 0
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check if line matches a book title
        matched = False
        for full_title, short_name in book_mappings.items():
            # More flexible matching - check if title is in the line
            if full_title.lower() in line.lower() and len(line) < 200:
                # Found new book
                if current_book and current_section:
                    # Process previous book's verses
                    book_verse_count = process_book_verses(current_book, current_section, verses)
                    if book_verse_count > 0:
                        book_count += 1
                
                current_book = short_name
                current_section = ""
                matched = True
                print(f"  Found book: {short_name}")
                break
        
        if not matched:
            # Not a book header, add to current section
            if current_book:
                current_section += line + "\n"
    
    # Process final book
    if current_book and current_section:
        book_verse_count = process_book_verses(current_book, current_section, verses)
        if book_verse_count > 0:
            book_count += 1
    
    print(f"  Processed {book_count} books")
    
    print(f"\nExtracted {len(verses):,} verses")
    return verses

def process_book_verses(book, text, verses_list):
    """Extract verses from a single book's text"""
    
    verse_pattern = re.compile(r'^(\d+):(\d+)\s+(.+?)$', re.MULTILINE)
    
    matches = verse_pattern.findall(text)
    initial_count = len(verses_list)
    
    for chapter, verse, verse_text in matches:
        verse_text = verse_text.strip()
        if verse_text:  # Only add non-empty verses
            verses_list.append({
                "book": book,
                "chapter": int(chapter),
                "verse": int(verse),
                "language": "English",
                "source_file": "pg10.txt",
                "text": verse_text
            })
    
    return len(verses_list) - initial_count

def save_jsonl(verses, output_file):
    """Save verses as JSONL (one JSON per line)"""
    
    output_path = Path(output_file)
    
    with output_path.open('w', encoding='utf-8') as f:
        for verse in verses:
            json.dump(verse, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"\nSaved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

def main():
    input_file = Path("pg10.txt")
    output_file = Path("kjv_chunks.jsonl")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        print("Run download_kjv.py first")
        return
    
    print("=" * 60)
    print("KJV Verse Extraction Pipeline")
    print("=" * 60)
    
    # Read KJV text
    print(f"\nReading {input_file}...")
    text = input_file.read_text(encoding='utf-8')
    print(f"Original size: {len(text):,} characters")
    
    # Clean Gutenberg headers/footers
    print("\nCleaning Project Gutenberg headers/footers...")
    cleaned_text = clean_gutenberg_text(text)
    
    # Extract verses
    print("\nExtracting verses...")
    verses = extract_kjv_verses(cleaned_text)
    
    if not verses:
        print("ERROR: No verses extracted!")
        print("Sample text:")
        print(cleaned_text[:1000])
        return
    
    # Show sample
    print("\nSample verses:")
    for i, v in enumerate(verses[:3]):
        print(f"\n{i+1}. {v['book']} {v['chapter']}:{v['verse']}")
        print(f"   {v['text'][:100]}...")
    
    # Save to JSONL
    print("\nSaving to JSONL...")
    save_jsonl(verses, output_file)
    
    print("\n" + "=" * 60)
    print("✓ KJV verse extraction complete")
    print(f"✓ Output: {output_file}")
    print(f"✓ Total verses: {len(verses):,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
