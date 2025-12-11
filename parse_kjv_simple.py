"""
Robust KJV parser - extracts full verse text from Project Gutenberg pg10.txt
Outputs: kjv_chunks.jsonl (one JSON object per line)
"""

import json
import re
from pathlib import Path

def main():
    input_file = Path("pg10_normalized.txt")
    output_file = Path("kjv_chunks.jsonl")

    text = input_file.read_text(encoding="utf-8")
    
    print(f"Processing {len(text):,} characters...")

    # Linear scan: find verses and assign to most recent book header
    # Regex captures verse text until next verse marker (accounting for whitespace)
    verse_pattern = re.compile(r"(\d+):(\d+)\s+(.+?)(?=\s*\d+:\d+|\Z)", re.DOTALL)
    
    # Build a map of all book header positions (simple - no TOC or duplicates in cleaned file)
    book_headers = []
    for marker, book_name in BOOK_MARKERS:
        # For short markers (like "Joel", "Amos"), require them to be standalone on a line
        if len(marker) <= 10:
            # Must be preceded and followed by blank lines
            pattern = r'\n\n' + re.escape(marker) + r'\n\n'
            match = re.search(pattern, text)
            if match:
                pos = match.start() + 2  # Position after the first \n\n
                book_headers.append((pos, book_name))
        else:
            # Longer markers can be found normally
            pos = text.find(marker)
            if pos >= 0:
                book_headers.append((pos, book_name))
    
    book_headers.sort()  # Sort by position
    print(f"Found {len(book_headers)} book headers")
    
    verses = []
    for match in verse_pattern.finditer(text):
        # Find which book this verse belongs to (last header before verse)
        current_book = "Unknown"
        verse_pos = match.start()
        for header_pos, book_name in book_headers:
            if header_pos <= verse_pos:
                current_book = book_name
            else:
                break
        
        chapter = int(match.group(1))
        verse = int(match.group(2))
        verse_text = " ".join(match.group(3).split())

        verses.append({
            "book": current_book,
            "chapter": chapter,
            "verse": verse,
            "language": "English",
            "source_file": "pg10.txt",
            "text": verse_text
        })

    print(f"Extracted {len(verses):,} verses")

    # Validation: check book coverage
    books_seen = sorted(set(v["book"] for v in verses))
    print(f"Books parsed: {len(books_seen)}")
    if len(books_seen) != 66:
        missing = sorted(set(b for _, b in BOOK_MARKERS) - set(books_seen))
        print("WARNING: Missing books:", missing)

    # Show sample
    print("\nFirst 10 verses:")
    for v in verses[:10]:
        print(f"  {v['book']} {v['chapter']}:{v['verse']} - {v['text'][:60]}...")

    print("\nLast verse:", verses[-1])

    # Save JSONL
    with output_file.open("w", encoding="utf-8") as f:
        for v in verses:
            json.dump(v, f, ensure_ascii=False)
            f.write("\n")

    print(f"\nSaved to {output_file}")
    print("✓ KJV verse extraction complete")

# Canonical book markers
BOOK_MARKERS = [
    ("The First Book of Moses: Called Genesis", "Genesis"),
    ("The Second Book of Moses: Called Exodus", "Exodus"),
    ("The Third Book of Moses: Called Leviticus", "Leviticus"),
    ("The Fourth Book of Moses: Called Numbers", "Numbers"),
    ("The Fifth Book of Moses: Called Deuteronomy", "Deuteronomy"),
    ("The Book of Joshua", "Joshua"),
    ("The Book of Judges", "Judges"),
    ("The Book of Ruth", "Ruth"),
    ("The First Book of Samuel", "1 Samuel"),
    ("The Second Book of Samuel", "2 Samuel"),
    ("The First Book of the Kings", "1 Kings"),
    ("The Second Book of the Kings", "2 Kings"),
    ("The First Book of the Chronicles", "1 Chronicles"),
    ("The Second Book of the Chronicles", "2 Chronicles"),
    ("Ezra", "Ezra"),
    ("The Book of Nehemiah", "Nehemiah"),
    ("The Book of Esther", "Esther"),
    ("The Book of Job", "Job"),
    ("The Book of Psalms", "Psalms"),
    ("The Proverbs", "Proverbs"),
    ("Ecclesiastes", "Ecclesiastes"),
    ("The Song of Solomon", "Song of Solomon"),
    ("The Book of the Prophet Isaiah", "Isaiah"),
    ("The Book of the Prophet Jeremiah", "Jeremiah"),
    ("The Lamentations of Jeremiah", "Lamentations"),
    ("The Book of the Prophet Ezekiel", "Ezekiel"),
    ("The Book of Daniel", "Daniel"),
    ("Hosea", "Hosea"),
    ("Joel", "Joel"),
    ("Amos", "Amos"),
    ("Obadiah", "Obadiah"),
    ("Jonah", "Jonah"),
    ("Micah", "Micah"),
    ("Nahum", "Nahum"),
    ("Habakkuk", "Habakkuk"),
    ("Zephaniah", "Zephaniah"),
    ("Haggai", "Haggai"),
    ("Zechariah", "Zechariah"),
    ("Malachi", "Malachi"),
    ("The Gospel According to Saint Matthew", "Matthew"),
    ("The Gospel According to Saint Mark", "Mark"),
    ("The Gospel According to Saint Luke", "Luke"),
    ("The Gospel According to Saint John", "John"),
    ("The Acts of the Apostles", "Acts"),
    ("The Epistle of Paul the Apostle to the Romans", "Romans"),
    ("The First Epistle of Paul the Apostle to the Corinthians", "1 Corinthians"),
    ("The Second Epistle of Paul the Apostle to the Corinthians", "2 Corinthians"),
    ("The Epistle of Paul the Apostle to the Galatians", "Galatians"),
    ("The Epistle of Paul the Apostle to the Ephesians", "Ephesians"),
    ("The Epistle of Paul the Apostle to the Philippians", "Philippians"),
    ("The Epistle of Paul the Apostle to the Colossians", "Colossians"),
    ("The First Epistle of Paul the Apostle to the Thessalonians", "1 Thessalonians"),
    ("The Second Epistle of Paul the Apostle to the Thessalonians", "2 Thessalonians"),
    ("The First Epistle of Paul the Apostle to Timothy", "1 Timothy"),
    ("The Second Epistle of Paul the Apostle to Timothy", "2 Timothy"),
    ("The Epistle of Paul the Apostle to Titus", "Titus"),
    ("The Epistle of Paul the Apostle to Philemon", "Philemon"),
    ("The Epistle of Paul the Apostle to the Hebrews", "Hebrews"),
    ("The General Epistle of James", "James"),
    ("The First Epistle General of Peter", "1 Peter"),
    ("The Second General Epistle of Peter", "2 Peter"),
    ("The First Epistle General of John", "1 John"),
    ("The Second Epistle General of John", "2 John"),
    ("The Third Epistle General of John", "3 John"),
    ("The General Epistle of Jude", "Jude"),
    ("The Revelation of Saint John the Divine", "Revelation"),
]

if __name__ == "__main__":
    main()
