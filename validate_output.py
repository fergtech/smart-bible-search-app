"""
Validate Biblical Verses Output
================================
Validates the structure and content of processed biblical verses.
"""

import json
from pathlib import Path
from collections import defaultdict

def validate_verse_structure(verse: dict) -> list:
    """Validate a single verse structure and return issues."""
    issues = []
    
    # Required fields
    required_fields = ['book', 'chapter', 'verse', 'language', 'source_file', 'text']
    for field in required_fields:
        if field not in verse:
            issues.append(f"Missing required field: {field}")
    
    # Type checks
    if 'chapter' in verse and not isinstance(verse['chapter'], int):
        issues.append(f"Chapter should be int, got {type(verse['chapter'])}")
    
    if 'verse' in verse and not isinstance(verse['verse'], int):
        issues.append(f"Verse should be int, got {type(verse['verse'])}")
    
    # Content checks
    if 'text' in verse and not verse['text'].strip():
        issues.append("Empty text content")
    
    if 'text' in verse and len(verse['text']) < 3:
        issues.append(f"Suspiciously short text: '{verse['text']}'")
    
    return issues

def analyze_coverage(verses: list):
    """Analyze coverage by book, language, etc."""
    stats = {
        'total_verses': len(verses),
        'by_language': defaultdict(int),
        'by_book': defaultdict(int),
        'by_testament': {'Old': 0, 'New': 0},
        'chapter_ranges': defaultdict(lambda: {'min': float('inf'), 'max': 0}),
    }
    
    ot_books = ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges']
    
    for verse in verses:
        # Language
        stats['by_language'][verse['language']] += 1
        
        # Book
        book = verse['book']
        stats['by_book'][book] += 1
        
        # Testament
        if book in ot_books:
            stats['by_testament']['Old'] += 1
        else:
            stats['by_testament']['New'] += 1
        
        # Chapter ranges
        chapter = verse['chapter']
        if chapter > 0:
            stats['chapter_ranges'][book]['min'] = min(stats['chapter_ranges'][book]['min'], chapter)
            stats['chapter_ranges'][book]['max'] = max(stats['chapter_ranges'][book]['max'], chapter)
    
    return stats

def print_sample_verses(verses: list, book: str, num: int = 3):
    """Print sample verses from a specific book."""
    print(f"\n📖 Sample from {book}:")
    book_verses = [v for v in verses if v['book'] == book]
    
    for verse in book_verses[:num]:
        ref = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
        text_preview = verse['text'][:80] + ('...' if len(verse['text']) > 80 else '')
        print(f"  {ref}")
        print(f"    {text_preview}")

def main():
    print("=" * 70)
    print("Biblical Verses Validation Report")
    print("=" * 70)
    
    # Load JSON
    json_path = Path("biblical_verses_enhanced.json")
    
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        print("\nRun: python preprocess_enhanced.py")
        return
    
    print(f"\n📄 Loading: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        verses = json.load(f)
    
    print(f"✓ Loaded {len(verses)} verses")
    
    # Validation
    print("\n" + "=" * 70)
    print("Validation Results")
    print("=" * 70)
    
    total_issues = 0
    verses_with_issues = 0
    
    for i, verse in enumerate(verses):
        issues = validate_verse_structure(verse)
        if issues:
            verses_with_issues += 1
            total_issues += len(issues)
            if verses_with_issues <= 3:  # Show first 3 problematic verses
                print(f"\n❌ Verse {i+1} issues:")
                for issue in issues:
                    print(f"   - {issue}")
                print(f"   Verse: {verse}")
    
    if total_issues == 0:
        print("✅ All verses passed validation!")
    else:
        print(f"\n⚠️  Found {total_issues} issues in {verses_with_issues} verses")
    
    # Coverage analysis
    print("\n" + "=" * 70)
    print("Coverage Analysis")
    print("=" * 70)
    
    stats = analyze_coverage(verses)
    
    print(f"\n📊 Total verses: {stats['total_verses']}")
    
    print(f"\n🌍 By Language:")
    for lang, count in sorted(stats['by_language'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count} verses")
    
    print(f"\n📚 By Testament:")
    print(f"  Old Testament: {stats['by_testament']['Old']} verses")
    print(f"  New Testament: {stats['by_testament']['New']} verses")
    
    print(f"\n📖 Top 10 Books by Verse Count:")
    top_books = sorted(stats['by_book'].items(), key=lambda x: x[1], reverse=True)[:10]
    for book, count in top_books:
        chapter_range = stats['chapter_ranges'][book]
        if chapter_range['min'] != float('inf'):
            print(f"  {book}: {count} verses (Chapters {chapter_range['min']}-{chapter_range['max']})")
        else:
            print(f"  {book}: {count} verses")
    
    # Sample verses
    print("\n" + "=" * 70)
    print("Sample Verses")
    print("=" * 70)
    
    if stats['by_book']['Matthew'] > 0:
        print_sample_verses(verses, 'Matthew', 3)
    
    if stats['by_book']['John'] > 0:
        print_sample_verses(verses, 'John', 3)
    
    if stats['by_book']['Romans'] > 0:
        print_sample_verses(verses, 'Romans', 3)
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    print(f"""
✅ Successfully processed: {stats['total_verses']} verses
📚 Books covered: {len(stats['by_book'])}
🌍 Languages: {len(stats['by_language'])}
📄 Output file: {json_path.name} ({json_path.stat().st_size / 1024:.1f} KB)

Next steps:
1. Generate embeddings for semantic search
2. Add lexicon metadata (Strong's numbers, etc.)
3. Process Hebrew Old Testament texts
4. Add cross-references between verses
    """)

if __name__ == "__main__":
    main()
