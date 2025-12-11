"""
Comprehensive Project Audit
============================
Analyzes all files and identifies missing/incomplete components.
"""

import json
from pathlib import Path
from collections import defaultdict

def audit_json_file(filepath):
    """Audit a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = {
            'exists': True,
            'total_entries': len(data),
            'keys': list(data[0].keys()) if data else [],
            'sample_book': data[0].get('book', 'N/A') if data else 'N/A',
            'has_lexicon': 'lexicon' in data[0] if data else False,
            'unique_books': len(set(item.get('book', 'Unknown') for item in data)),
            'unknown_count': sum(1 for item in data if item.get('book') == 'Unknown'),
            'languages': {}
        }
        
        # Count languages
        for item in data:
            lang = item.get('language', 'Unknown')
            result['languages'][lang] = result['languages'].get(lang, 0) + 1
        
        return result
    except Exception as e:
        return {'exists': False, 'error': str(e)}

def main():
    print("=" * 70)
    print("COMPREHENSIVE PROJECT AUDIT")
    print("=" * 70)
    
    base_path = Path("h:/Apps/book-intel")
    
    # Check output files
    print("\n1. OUTPUT FILES")
    print("-" * 70)
    
    output_files = [
        "biblical_verses.json",
        "biblical_verses_enhanced.json",
        "biblical_verses_with_strongs.json",
        "hebrew_aramaic_verses.json"
    ]
    
    for filename in output_files:
        filepath = base_path / filename
        print(f"\n{filename}:")
        
        if filepath.exists():
            audit = audit_json_file(filepath)
            if audit['exists']:
                print(f"  Size: {filepath.stat().st_size / 1024:.1f} KB")
                print(f"  Entries: {audit['total_entries']}")
                print(f"  Unique books: {audit['unique_books']}")
                print(f"  Languages: {audit['languages']}")
                if audit['has_lexicon']:
                    print(f"  Has lexicon: YES")
                if audit['unknown_count'] > 0:
                    print(f"  WARNING: {audit['unknown_count']} Unknown books")
            else:
                print(f"  ERROR: {audit.get('error')}")
        else:
            print("  STATUS: NOT FOUND")
    
    # Check data directories
    print("\n\n2. DATA DIRECTORIES")
    print("-" * 70)
    
    dirs_to_check = ["lxx_data", "sblgnt_data", "strongs_data"]
    
    for dirname in dirs_to_check:
        dirpath = base_path / dirname
        print(f"\n{dirname}/:")
        
        if dirpath.exists():
            files = list(dirpath.glob("*"))
            if files:
                print(f"  Files: {len(files)}")
                for f in files[:5]:
                    print(f"    - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more")
            else:
                print("  STATUS: EMPTY (NO FILES)")
        else:
            print("  STATUS: DOES NOT EXIST")
    
    # Check source PDFs
    print("\n\n3. SOURCE FILES")
    print("-" * 70)
    
    pdfs = [
        "Westminster Leningrad Codex (Hebrew).pdf",
        "Targum Onkelos (Genesis & Exodus).pdf"
    ]
    
    for pdf in pdfs:
        pdfpath = base_path / pdf
        print(f"\n{pdf}:")
        if pdfpath.exists():
            print(f"  Size: {pdfpath.stat().st_size / 1024 / 1024:.1f} MB")
            print(f"  STATUS: EXISTS")
        else:
            print(f"  STATUS: NOT FOUND")
    
    # Critical issues summary
    print("\n\n4. CRITICAL ISSUES")
    print("-" * 70)
    
    issues = []
    
    # Check if lxx_data is empty
    if not list((base_path / "lxx_data").glob("*")):
        issues.append("lxx_data folder is EMPTY - Greek OT not downloaded")
    
    # Check if strongs_data is empty
    if not list((base_path / "strongs_data").glob("*")):
        issues.append("strongs_data folder is EMPTY - Strong's lexicon not downloaded")
    
    # Check hebrew verses
    hebrew_path = base_path / "hebrew_aramaic_verses.json"
    if hebrew_path.exists():
        audit = audit_json_file(hebrew_path)
        if audit['exists'] and audit['unknown_count'] > 0:
            issues.append(f"Hebrew verses have {audit['unknown_count']} Unknown books - needs proper parsing")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue}")
    else:
        print("\nNo critical issues found!")
    
    # Recommendations
    print("\n\n5. RECOMMENDATIONS")
    print("-" * 70)
    
    print("""
1. Download Greek OT (LXX) structured data
   - Repository has TSV files that need to be downloaded
   - Located in: 11_end-users_files directory

2. Download Strong's Lexicon data from a working source
   - Current URLs are 404
   - Need to find alternative source or use embedded lexicon

3. Improve Hebrew PDF extraction
   - Current extraction has encoding issues
   - Consider using structured WLC data from GitHub instead of PDF
   - Or implement better font mapping for PDF

4. Expand Strong's lexicon coverage
   - Currently only 20 sample words (14.9% coverage)
   - Need full Greek and Hebrew lexicons

5. Generate embeddings for semantic search
   - Install: sentence-transformers
   - Create vector embeddings for all verses
    """)
    
    print("=" * 70)

if __name__ == "__main__":
    main()
