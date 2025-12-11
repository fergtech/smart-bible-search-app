"""
Enhanced Biblical Text Preprocessing Script
============================================
Processes biblical texts with proper verse-level parsing using downloaded structured data.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@dataclass
class VerseChunk:
    """Represents a single verse chunk."""
    book: str
    chapter: int
    verse: int
    language: str
    source_file: str
    text: str
    lexicon: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


class EnhancedBiblicalProcessor:
    """Enhanced processor with verse mapping integration."""
    
    # Book name mappings
    BOOK_MAPPINGS = {
        'Matt': 'Matthew', '1Cor': '1 Corinthians', '2Cor': '2 Corinthians',
        'Gal': 'Galatians', 'Eph': 'Ephesians', 'Phil': 'Philippians',
        'Col': 'Colossians', '1Thess': '1 Thessalonians', '2Thess': '2 Thessalonians',
        '1Tim': '1 Timothy', '2Tim': '2 Timothy', 'Titus': 'Titus',
        'Phlm': 'Philemon', 'Heb': 'Hebrews', 'Jas': 'James',
        '1Pet': '1 Peter', '2Pet': '2 Peter', '1John': '1 John',
        '2John': '2 John', '3John': '3 John', 'Jude': 'Jude',
        'Rev': 'Revelation', 'Rom': 'Romans', 'Mark': 'Mark',
        'Luke': 'Luke', 'John': 'John', 'Acts': 'Acts'
    }
    
    def __init__(self, output_path: str = "biblical_verses_enhanced.json"):
        self.output_path = output_path
        self.chunks: List[VerseChunk] = []
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode text to NFC form."""
        return unicodedata.normalize('NFC', text)
    
    def normalize_greek_text(self, text: str) -> str:
        """Normalize Greek text specifically."""
        text = self.normalize_unicode(text)
        # Remove text-critical apparatus markers
        text = re.sub(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]', '', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def normalize_hebrew_text(self, text: str) -> str:
        """Normalize Hebrew text specifically."""
        text = self.normalize_unicode(text)
        # Remove vowel points and cantillation marks (optional - keep for now)
        # text = re.sub(r'[\u0591-\u05C7]', '', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def parse_sblgnt_file(self, file_path: Path) -> List[VerseChunk]:
        """Parse SBLGNT text file with verse markers."""
        chunks = []
        book_abbr = file_path.stem  # e.g., "Matt"
        book_name = self.BOOK_MAPPINGS.get(book_abbr, book_abbr)
        
        print(f"  Parsing {book_name}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            verse_count = 0
            for line in lines[1:]:  # Skip title line
                line = line.strip()
                if not line:
                    continue
                
                # Parse format: "Book C:V   text"
                # Example: "Matt 1:1   Βίβλος γενέσεως..."
                match = re.match(r'(\w+)\s+(\d+):(\d+)\s+(.*)', line)
                if match:
                    chapter = int(match.group(2))
                    verse = int(match.group(3))
                    text = match.group(4)
                    
                    # Normalize Greek text
                    text = self.normalize_greek_text(text)
                    
                    if text:  # Skip empty verses
                        chunk = VerseChunk(
                            book=book_name,
                            chapter=chapter,
                            verse=verse,
                            language="Greek",
                            source_file=file_path.name,
                            text=text
                        )
                        chunks.append(chunk)
                        verse_count += 1
            
            print(f"    ✓ Extracted {verse_count} verses")
        
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        return chunks
    
    def process_sblgnt_directory(self, directory: Path):
        """Process all SBLGNT files in directory."""
        print("\n📖 Processing SBLGNT (Greek New Testament)...")
        
        sblgnt_dir = directory / "sblgnt_data"
        if not sblgnt_dir.exists():
            print(f"  Directory not found: {sblgnt_dir}")
            print(f"  Run: python download_structured_data.py first")
            return
        
        # Get all .txt files
        txt_files = sorted(sblgnt_dir.glob("*.txt"))
        
        if not txt_files:
            print(f"  No .txt files found in {sblgnt_dir}")
            return
        
        print(f"  Found {len(txt_files)} book files")
        
        for txt_file in txt_files:
            book_chunks = self.parse_sblgnt_file(txt_file)
            self.chunks.extend(book_chunks)
    
    def process_pdf_with_hebrew(self, pdf_path: Path) -> List[VerseChunk]:
        """Process Hebrew PDF with improved extraction."""
        chunks = []
        
        if not PDF_AVAILABLE:
            print(f"  Skipping {pdf_path.name}: PyMuPDF not available")
            return chunks
        
        print(f"\n📖 Processing {pdf_path.name}...")
        
        try:
            doc = fitz.open(str(pdf_path))
            
            # Extract text from pages (skip preface pages)
            for page_num in range(min(5, len(doc))):  # Process first 5 pages as sample
                page = doc[page_num]
                text = page.get_text()
                
                # Look for Hebrew text (right-to-left characters)
                hebrew_pattern = r'[\u0590-\u05FF]+'
                hebrew_matches = re.findall(hebrew_pattern, text)
                
                if hebrew_matches:
                    print(f"  Found Hebrew text on page {page_num + 1}")
                    # For now, store as paragraph chunks
                    # Full implementation would need better verse parsing
                    for match in hebrew_matches[:5]:  # Limit per page
                        normalized = self.normalize_hebrew_text(match)
                        if len(normalized) > 20:  # Meaningful length
                            chunk = VerseChunk(
                                book="Unknown",
                                chapter=0,
                                verse=0,
                                language="Hebrew",
                                source_file=pdf_path.name,
                                text=normalized
                            )
                            chunks.append(chunk)
            
            doc.close()
            print(f"  ✓ Extracted {len(chunks)} Hebrew text segments")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        return chunks
    
    def process_all(self, directory: Path):
        """Process all biblical texts."""
        print("=" * 70)
        print("Enhanced Biblical Text Preprocessing Pipeline")
        print("=" * 70)
        
        # Process SBLGNT (Greek NT) - structured data
        self.process_sblgnt_directory(directory)
        
        # Process Hebrew PDF (sample extraction)
        hebrew_pdf = directory / "Westminster Leningrad Codex (Hebrew).pdf"
        if hebrew_pdf.exists():
            hebrew_chunks = self.process_pdf_with_hebrew(hebrew_pdf)
            self.chunks.extend(hebrew_chunks[:50])  # Limit Hebrew samples
        
        print("\n" + "=" * 70)
        print(f"✓ Processing complete! Total chunks: {len(self.chunks)}")
        print("=" * 70)
    
    def save_output(self):
        """Save processed chunks to JSON."""
        output_data = [chunk.to_dict() for chunk in self.chunks]
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Saved {len(output_data)} verse chunks to: {self.output_path}")
        
        # Statistics
        stats = {
            'total': len(self.chunks),
            'by_language': {},
            'by_book': {}
        }
        
        for chunk in self.chunks:
            # Language stats
            stats['by_language'][chunk.language] = stats['by_language'].get(chunk.language, 0) + 1
            # Book stats
            stats['by_book'][chunk.book] = stats['by_book'].get(chunk.book, 0) + 1
        
        print("\n📊 Statistics:")
        print(f"  Languages:")
        for lang, count in sorted(stats['by_language'].items()):
            print(f"    {lang}: {count} verses")
        
        print(f"\n  Books (top 10):")
        for book, count in sorted(stats['by_book'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {book}: {count} verses")
    
    def print_sample(self, num_samples: int = 5):
        """Print sample chunks."""
        print(f"\n{'=' * 70}")
        print(f"Sample Output (first {num_samples} chunks):")
        print('=' * 70)
        
        for i, chunk in enumerate(self.chunks[:num_samples]):
            print(f"\nChunk {i+1} - {chunk.book} {chunk.chapter}:{chunk.verse}")
            print(f"  Language: {chunk.language}")
            print(f"  Text: {chunk.text[:100]}{'...' if len(chunk.text) > 100 else ''}")


def main():
    """Main execution."""
    work_dir = Path(__file__).parent
    
    processor = EnhancedBiblicalProcessor()
    processor.process_all(work_dir)
    
    if processor.chunks:
        processor.save_output()
        processor.print_sample()
    else:
        print("\n⚠ No chunks extracted!")
        print("\nPlease ensure:")
        print("  1. Run: python download_structured_data.py")
        print("  2. SBLGNT files exist in sblgnt_data/ directory")


if __name__ == "__main__":
    main()
