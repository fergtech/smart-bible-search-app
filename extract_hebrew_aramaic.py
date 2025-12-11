"""
Hebrew & Aramaic Text Extractor
================================
Extracts Hebrew text from Westminster Leningrad Codex and Targum Onkelos PDFs.
Handles special font encodings and creates verse-level chunks.
"""

import fitz
import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

@dataclass
class HebrewVerse:
    """Hebrew verse structure."""
    book: str
    chapter: int
    verse: int
    language: str
    source_file: str
    text: str
    transliteration: str = ""
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        return {k: v for k, v in result.items() if v}


class HebrewPDFExtractor:
    """Extracts and processes Hebrew text from PDFs."""
    
    # Hebrew book names (English and Hebrew)
    HEBREW_BOOKS = {
        'Genesis': ('בראשית', 'tyVארb', 'Bereshit'),
        'Exodus': ('שמות', 'twmV', 'Shemot'),
        'Leviticus': ('ויקרא', 'ארqyw', 'Vayikra'),
        'Numbers': ('במדבר', 'rbdmb', 'Bamidbar'),
        'Deuteronomy': ('דברים', 'Myrbd', 'Devarim'),
    }
    
    def __init__(self):
        self.verses: List[HebrewVerse] = []
        self.current_book = "Unknown"
        self.current_chapter = 0
        self.current_verse = 0
    
    def detect_book_name(self, text: str) -> str:
        """Detect book name from text."""
        for english_name, (hebrew, encoded, trans) in self.HEBREW_BOOKS.items():
            if encoded in text or hebrew in text or trans.lower() in text.lower():
                return english_name
        return None
    
    def extract_verse_number(self, text: str) -> Tuple[int, int]:
        """
        Extract chapter and verse numbers.
        Hebrew PDFs often have superscript numbers or special markers.
        """
        # Pattern 1: Look for isolated numbers (likely verse numbers)
        numbers = re.findall(r'\b(\d+)\b', text)
        
        if numbers:
            # Heuristic: first number might be chapter, second verse
            if len(numbers) >= 2:
                return int(numbers[0]), int(numbers[1])
            elif len(numbers) == 1:
                return 0, int(numbers[0])
        
        return 0, 0
    
    def clean_hebrew_text(self, text: str) -> str:
        """Clean and normalize Hebrew text."""
        if not text:
            return ""
        
        # Remove common PDF artifacts
        text = re.sub(r'[�\ufffd]', '', text)
        
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Clean excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def process_wlc_pdf(self, pdf_path: Path) -> List[HebrewVerse]:
        """
        Process Westminster Leningrad Codex PDF.
        This PDF has complex encoding - we'll extract what we can.
        """
        print(f"\n📖 Processing Westminster Leningrad Codex...")
        print(f"  Path: {pdf_path}")
        
        verses = []
        
        try:
            doc = fitz.open(str(pdf_path))
            print(f"  Total pages: {len(doc)}")
            
            # Process pages (skip preface pages 1-5)
            for page_num in range(6, min(50, len(doc))):  # Process first 44 pages as sample
                page = doc[page_num]
                
                # Extract text with different methods
                text = page.get_text()
                
                # Try to detect book
                book = self.detect_book_name(text)
                if book:
                    self.current_book = book
                    print(f"  📚 Found book: {book} on page {page_num + 1}")
                
                # Extract blocks of text
                blocks = page.get_text("blocks")
                
                for block in blocks:
                    if len(block) < 5:
                        continue
                    
                    block_text = block[4] if isinstance(block[4], str) else ""
                    
                    # Check if contains Hebrew characters
                    has_hebrew = any('\u0590' <= c <= '\u05FF' for c in block_text)
                    
                    if has_hebrew or len(block_text) > 30:
                        # Try to extract verse numbers
                        chapter, verse = self.extract_verse_number(block_text)
                        
                        if chapter > 0:
                            self.current_chapter = chapter
                        if verse > 0:
                            self.current_verse = verse
                        
                        # Clean text
                        cleaned = self.clean_hebrew_text(block_text)
                        
                        if len(cleaned) > 10:  # Meaningful length
                            hebrew_verse = HebrewVerse(
                                book=self.current_book if self.current_book != "Unknown" else "Genesis",
                                chapter=self.current_chapter if self.current_chapter > 0 else 1,
                                verse=self.current_verse if self.current_verse > 0 else 1,
                                language="Hebrew",
                                source_file=pdf_path.name,
                                text=cleaned
                            )
                            verses.append(hebrew_verse)
                            
                            if self.current_verse > 0:
                                self.current_verse += 1
            
            doc.close()
            print(f"  ✓ Extracted {len(verses)} Hebrew text segments")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        return verses
    
    def process_targum_pdf(self, pdf_path: Path) -> List[HebrewVerse]:
        """Process Targum Onkelos PDF (Aramaic)."""
        print(f"\n📖 Processing Targum Onkelos...")
        print(f"  Path: {pdf_path}")
        
        verses = []
        
        try:
            doc = fitz.open(str(pdf_path))
            print(f"  Total pages: {len(doc)}")
            
            # Process first several pages
            for page_num in range(min(20, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                
                # Similar extraction logic
                blocks = page.get_text("blocks")
                
                for block in blocks:
                    if len(block) < 5:
                        continue
                    
                    block_text = block[4] if isinstance(block[4], str) else ""
                    
                    # Check for Aramaic/Hebrew characters
                    has_text = any('\u0590' <= c <= '\u05FF' for c in block_text)
                    
                    if has_text and len(block_text) > 20:
                        cleaned = self.clean_hebrew_text(block_text)
                        
                        if len(cleaned) > 15:
                            aramaic_verse = HebrewVerse(
                                book="Genesis",  # Targum covers Genesis & Exodus
                                chapter=1,
                                verse=1,
                                language="Aramaic",
                                source_file=pdf_path.name,
                                text=cleaned
                            )
                            verses.append(aramaic_verse)
            
            doc.close()
            print(f"  ✓ Extracted {len(verses)} Aramaic text segments")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        return verses


def main():
    """Main extraction process."""
    print("=" * 70)
    print("Hebrew & Aramaic Text Extraction")
    print("=" * 70)
    
    extractor = HebrewPDFExtractor()
    all_verses = []
    
    # Process Westminster Leningrad Codex
    wlc_path = Path("Westminster Leningrad Codex (Hebrew).pdf")
    if wlc_path.exists():
        wlc_verses = extractor.process_wlc_pdf(wlc_path)
        all_verses.extend(wlc_verses)
    
    # Process Targum Onkelos
    targum_path = Path("Targum Onkelos (Genesis & Exodus).pdf")
    if targum_path.exists():
        targum_verses = extractor.process_targum_pdf(targum_path)
        all_verses.extend(targum_verses)
    
    # Save output
    if all_verses:
        output_path = "hebrew_aramaic_verses.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([v.to_dict() for v in all_verses], f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 70)
        print(f"✓ Saved {len(all_verses)} verses to {output_path}")
        print("=" * 70)
        
        # Show samples
        print("\n📄 Sample verses:")
        for i, verse in enumerate(all_verses[:3]):
            print(f"\n{i+1}. {verse.book} {verse.chapter}:{verse.verse} ({verse.language})")
            print(f"   {verse.text[:100]}...")
    else:
        print("\n⚠️  No verses extracted")


if __name__ == "__main__":
    main()
