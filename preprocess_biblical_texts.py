"""
Biblical Text Preprocessing Script
===================================
Extracts verse-level chunks from PDF and text files, integrating lexicon metadata.

Processes:
1. Westminster Leningrad Codex (Hebrew).pdf - Hebrew Old Testament
2. Targum Onkelos (Genesis & Exodus).pdf - Aramaic Targum
3. Greek Old Testament (Septuagint, LXX).txt - Greek OT (from GitHub)
4. SBL Greek New Testament (SBLGNT).txt - Greek NT (from GitHub)

Output: structured JSON with verse-level chunks and lexicon metadata
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PyMuPDF not installed. PDF extraction will be skipped.")
    print("Install with: pip install PyMuPDF")


@dataclass
class VerseChunk:
    """Represents a single verse or paragraph chunk."""
    book: str
    chapter: Optional[int]
    verse: Optional[int]
    language: str
    source_file: str
    text: str
    lexicon: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


class BiblicalTextProcessor:
    """Main processor for biblical texts."""
    
    # Hebrew book names mapping (Tanakh order)
    HEBREW_BOOKS = {
        'Genesis': 'בראשית', 'Exodus': 'שמות', 'Leviticus': 'ויקרא',
        'Numbers': 'במדבר', 'Deuteronomy': 'דברים', 'Joshua': 'יהושע',
        'Judges': 'שופטים', 'Ruth': 'רות', '1 Samuel': 'שמואל א',
        '2 Samuel': 'שמואל ב', '1 Kings': 'מלכים א', '2 Kings': 'מלכים ב',
        'Isaiah': 'ישעיהו', 'Jeremiah': 'ירמיהו', 'Ezekiel': 'יחזקאל',
        'Psalms': 'תהלים', 'Proverbs': 'משלי', 'Job': 'איוב',
    }
    
    # Greek NT book names
    GREEK_NT_BOOKS = [
        'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
        '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
        'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
        '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews',
        'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John',
        'Jude', 'Revelation'
    ]
    
    def __init__(self, output_path: str = "biblical_verses.json"):
        self.output_path = output_path
        self.chunks: List[VerseChunk] = []
        self.lexicon_data: Dict[str, Any] = {}
    
    def normalize_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove common PDF artifacts
        text = re.sub(r'\s*\n\s*', ' ', text)
        # Trim
        text = text.strip()
        return text
    
    def extract_verse_markers(self, text: str) -> List[tuple]:
        """
        Extract verse markers from text.
        Returns list of (book, chapter, verse, start_pos, end_pos) tuples.
        """
        markers = []
        
        # Pattern 1: English format - Book Chapter:Verse (e.g., "Genesis 1:1", "Matt 5:3")
        pattern_en = r'([12]?\s*[A-Za-z]+)\s+(\d+):(\d+)'
        
        for match in re.finditer(pattern_en, text):
            book = match.group(1).strip()
            chapter = int(match.group(2))
            verse = int(match.group(3))
            start = match.start()
            end = match.end()
            markers.append((book, chapter, verse, start, end))
        
        # Pattern 2: Superscript numbers often used in biblical texts
        # Look for standalone numbers that might be verse markers
        pattern_super = r'(?<!\d)(\d{1,3})(?!\d)'
        
        # Pattern 3: Hebrew chapter/verse structure (Genesis 1, etc. followed by verse numbers)
        # This would need more sophisticated parsing based on actual document structure
        
        return markers
    
    def process_pdf(self, pdf_path: Path, language: str) -> List[VerseChunk]:
        """Extract text from PDF and create verse chunks."""
        if not PDF_AVAILABLE:
            print(f"Skipping {pdf_path.name}: PyMuPDF not available")
            return []
        
        chunks = []
        print(f"\nProcessing PDF: {pdf_path.name}")
        
        try:
            doc = fitz.open(str(pdf_path))
            full_text = ""
            
            # Extract text from all pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                # Clean common PDF artifacts
                page_text = re.sub(r'\n+', '\n', page_text)
                page_text = re.sub(r'^\d+\s*$', '', page_text, flags=re.MULTILINE)  # Remove page numbers
                
                full_text += page_text + "\n"
            
            doc.close()
            
            # Try to detect verse markers
            verse_markers = self.extract_verse_markers(full_text)
            
            if verse_markers:
                print(f"  Found {len(verse_markers)} verse markers")
                # Split by verse markers
                for i, (book, chapter, verse, start, end) in enumerate(verse_markers):
                    # Get text until next marker or end
                    if i < len(verse_markers) - 1:
                        next_start = verse_markers[i + 1][3]
                        verse_text = full_text[end:next_start]
                    else:
                        verse_text = full_text[end:end+500]  # Get reasonable amount
                    
                    verse_text = self.normalize_text(verse_text)
                    
                    if verse_text and len(verse_text) > 5:  # Skip very short texts
                        chunk = VerseChunk(
                            book=book,
                            chapter=chapter,
                            verse=verse,
                            language=language,
                            source_file=pdf_path.name,
                            text=verse_text
                        )
                        chunks.append(chunk)
            else:
                print(f"  No verse markers found. Using paragraph-level chunking.")
                # Fallback: split by paragraphs
                paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
                
                for i, para in enumerate(paragraphs[:100]):  # Limit for safety
                    para = self.normalize_text(para)
                    if len(para) > 20:  # Skip very short paragraphs
                        chunk = VerseChunk(
                            book="Unknown",
                            chapter=None,
                            verse=None,
                            language=language,
                            source_file=pdf_path.name,
                            text=para
                        )
                        chunks.append(chunk)
        
        except Exception as e:
            print(f"  Error processing PDF: {e}")
        
        print(f"  Extracted {len(chunks)} chunks")
        return chunks
    
    def process_text_file(self, txt_path: Path, language: str) -> List[VerseChunk]:
        """Process text file with verse markers."""
        chunks = []
        print(f"\nProcessing text file: {txt_path.name}")
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if it's just a URL
            if content.strip().startswith('http'):
                print(f"  File contains only URL: {content.strip()}")
                print(f"  Note: Download actual text files from repository to process")
                return []
            
            # Extract verses
            verse_markers = self.extract_verse_markers(content)
            
            if verse_markers:
                print(f"  Found {len(verse_markers)} verse markers")
                for i, (book, chapter, verse, start, end) in enumerate(verse_markers):
                    if i < len(verse_markers) - 1:
                        next_start = verse_markers[i + 1][3]
                        verse_text = content[end:next_start]
                    else:
                        verse_text = content[end:end+500]
                    
                    verse_text = self.normalize_text(verse_text)
                    
                    if verse_text and len(verse_text) > 5:
                        chunk = VerseChunk(
                            book=book,
                            chapter=chapter,
                            verse=verse,
                            language=language,
                            source_file=txt_path.name,
                            text=verse_text
                        )
                        chunks.append(chunk)
        
        except Exception as e:
            print(f"  Error processing text file: {e}")
        
        print(f"  Extracted {len(chunks)} chunks")
        return chunks
    
    def load_lexicon_metadata(self, lexicon_path: Path):
        """Load lexicon metadata from JSON or structured text file."""
        # Placeholder for lexicon integration
        # This would parse Strong's numbers, root words, semantic domains, etc.
        print(f"\nLooking for lexicon metadata in: {lexicon_path}")
        if lexicon_path.exists():
            try:
                with open(lexicon_path, 'r', encoding='utf-8') as f:
                    self.lexicon_data = json.load(f)
                print(f"  Loaded lexicon data")
            except Exception as e:
                print(f"  Could not load lexicon: {e}")
    
    def enrich_with_lexicon(self, chunk: VerseChunk) -> VerseChunk:
        """Enrich verse chunk with lexicon metadata if available."""
        # Example: match Hebrew words to Strong's numbers
        # This is a simplified example - real implementation would be more sophisticated
        
        if not self.lexicon_data:
            return chunk
        
        # Search for matching lexicon entries based on book/chapter/verse
        key = f"{chunk.book}_{chunk.chapter}_{chunk.verse}"
        if key in self.lexicon_data:
            chunk.lexicon = self.lexicon_data[key]
        
        return chunk
    
    def process_all(self, directory: Path):
        """Process all biblical text files in directory."""
        print("=" * 70)
        print("Biblical Text Preprocessing Pipeline")
        print("=" * 70)
        
        # Process Westminster Leningrad Codex (Hebrew)
        hebrew_pdf = directory / "Westminster Leningrad Codex (Hebrew).pdf"
        if hebrew_pdf.exists():
            hebrew_chunks = self.process_pdf(hebrew_pdf, "Hebrew")
            self.chunks.extend(hebrew_chunks)
        
        # Process Targum Onkelos (Aramaic)
        targum_pdf = directory / "Targum Onkelos (Genesis & Exodus).pdf"
        if targum_pdf.exists():
            targum_chunks = self.process_pdf(targum_pdf, "Aramaic")
            self.chunks.extend(targum_chunks)
        
        # Process Greek Old Testament (Septuagint)
        lxx_txt = directory / "Greek Old Testament (Septuagint, LXX).txt"
        if lxx_txt.exists():
            lxx_chunks = self.process_text_file(lxx_txt, "Greek")
            self.chunks.extend(lxx_chunks)
        
        # Process Greek New Testament (SBLGNT)
        sblgnt_txt = directory / "SBL Greek New Testament (SBLGNT).txt"
        if sblgnt_txt.exists():
            sblgnt_chunks = self.process_text_file(sblgnt_txt, "Greek")
            self.chunks.extend(sblgnt_chunks)
        
        # Look for additional lexicon files
        lexicon_file = directory / "lexicon_metadata.json"
        if lexicon_file.exists():
            self.load_lexicon_metadata(lexicon_file)
            # Enrich chunks with lexicon data
            self.chunks = [self.enrich_with_lexicon(chunk) for chunk in self.chunks]
        
        print("\n" + "=" * 70)
        print(f"Processing complete! Total chunks: {len(self.chunks)}")
        print("=" * 70)
    
    def save_output(self):
        """Save processed chunks to JSON file."""
        output_data = [chunk.to_dict() for chunk in self.chunks]
        
        output_file = Path(self.output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Saved {len(output_data)} verse chunks to: {output_file}")
        
        # Print statistics
        languages = {}
        for chunk in self.chunks:
            languages[chunk.language] = languages.get(chunk.language, 0) + 1
        
        print("\nStatistics:")
        for lang, count in languages.items():
            print(f"  {lang}: {count} chunks")
    
    def print_sample(self, num_samples: int = 3):
        """Print sample chunks for verification."""
        print(f"\n{'=' * 70}")
        print(f"Sample Output (first {num_samples} chunks):")
        print('=' * 70)
        
        for i, chunk in enumerate(self.chunks[:num_samples]):
            print(f"\nChunk {i+1}:")
            print(json.dumps(chunk.to_dict(), ensure_ascii=False, indent=2))


def main():
    """Main execution function."""
    # Set working directory
    work_dir = Path(__file__).parent
    
    # Initialize processor
    processor = BiblicalTextProcessor(output_path="biblical_verses.json")
    
    # Process all files
    processor.process_all(work_dir)
    
    # Save results
    if processor.chunks:
        processor.save_output()
        processor.print_sample()
    else:
        print("\n⚠ No chunks were extracted. Please check:")
        print("  1. PDF files are readable")
        print("  2. PyMuPDF is installed (pip install PyMuPDF)")
        print("  3. Text files contain actual biblical text (not just URLs)")
        print("\nFor the .txt files that contain only GitHub URLs:")
        print("  - Clone or download the actual text files from those repositories")
        print("  - Place them in this directory")
        print("  - Re-run this script")


if __name__ == "__main__":
    main()
