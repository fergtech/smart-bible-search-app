# Biblical Text Preprocessing Pipeline

This directory contains scripts to process biblical texts from PDFs and text files into structured verse-level chunks suitable for semantic search and embedding.

## Files in This Directory

### Source Files
1. **Westminster Leningrad Codex (Hebrew).pdf** - Hebrew Old Testament  
2. **Targum Onkelos (Genesis & Exodus).pdf** - Aramaic Targum
3. **Greek Old Testament (Septuagint, LXX).txt** - URL to GitHub repository
4. **SBL Greek New Testament (SBLGNT).txt** - URL to GitHub repository

### Processing Scripts
- **preprocess_enhanced.py** - ⭐ **Main enhanced preprocessing script** (use this!)
- **download_structured_data.py** - Downloads structured text files from GitHub
- **explore_github_repos.py** - Explores GitHub repository structure
- preprocess_biblical_texts.py - Legacy script (initial version)

### Downloaded Data
- **sblgnt_data/** - Greek New Testament text files (27 books, verse-level)
- lxx_data/ - Greek Old Testament (to be implemented)

### Output Files
- **biblical_verses_enhanced.json** - ⭐ **Final output: 7,939 verses with proper structure**
- biblical_verses.json - Initial output (legacy)

## Current Status

### ✅ Completed
- **Greek New Testament**: 7,939 verses extracted with proper book/chapter/verse structure
- **Unicode normalization**: Greek text properly normalized (NFC)
- **Text cleaning**: Removed critical apparatus markers
- **Book name mapping**: Standardized book names (e.g., "Matt" → "Matthew")
- **JSON output**: Clean, structured format ready for embedding

### 🔄 Next Steps
- **Hebrew Old Testament**: Need structured data source (PDFs have complex encoding)
- **Greek Old Testament (LXX)**: Download structured files from repository
- **Lexicon integration**: Add Strong's numbers, root words, semantic domains
- **Aramaic Targum**: Parse PDF or find structured source

## How to Use

### Step 1: Install Dependencies

```bash
pip install PyMuPDF
```

### Step 2: Download Greek NT Texts

```bash
python download_structured_data.py
```

This downloads all 27 New Testament books from the SBLGNT repository with verse-level structure.

### Step 3: Run Enhanced Preprocessing

```bash
python preprocess_enhanced.py
```

This will:
- Parse SBLGNT text files (verse-level extraction)
- Normalize Greek Unicode text (NFC normalization)
- Remove critical apparatus markers
- Map book abbreviations to full names
- Create structured JSON output with 7,939 verses

## Output Format

Each verse chunk in `biblical_verses.json` has this structure:

```json
{
  "book": "Genesis",
  "chapter": 1,
  "verse": 1,
  "language": "Hebrew",
  "source_file": "Westminster Leningrad Codex (Hebrew).pdf",
  "text": "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ",
  "lexicon": {
    "strongs_number": "H3045",
    "root_word": "yada",
    "semantic_domain": ["knowledge", "intimacy"],
    "usage_notes": "contextual meaning..."
  }
}
```

**Fields:**
- `book`: Book name (e.g., Genesis, Matthew)
- `chapter`: Chapter number (or null for paragraph-level)
- `verse`: Verse number (or null for paragraph-level)
- `language`: Hebrew, Aramaic, or Greek
- `source_file`: Original filename
- `text`: The actual verse or paragraph text
- `lexicon`: Optional metadata (requires lexicon data files)

## Adding Lexicon Metadata

To add lexicon enrichment:

1. Create a `lexicon_metadata.json` file with this structure:
   ```json
   {
     "Genesis_1_1": {
       "strongs_number": "H1254",
       "root_word": "bara",
       "semantic_domain": ["creation", "divine activity"],
       "usage_notes": "Used exclusively for divine creation"
     }
   }
   ```

2. Place it in this directory

3. Re-run the preprocessing script

The script will automatically detect and integrate lexicon data.

## Improving Verse Detection

The current script uses basic verse marker patterns. To improve verse detection:

1. **For PDFs with Hebrew text:**
   - The Westminster Leningrad Codex uses Hebrew chapter/verse markers
   - May need OCR or better text extraction to identify verse boundaries
   - Consider using the WLC morphology files from the GitHub repository

2. **For Greek texts:**
   - Download actual text files from GitHub repositories
   - These typically have clear verse markers in the format: `Book Chapter:Verse`

3. **Pattern improvements:**
   - Add Hebrew/Greek numeral parsing
   - Detect book headings
   - Use lexicon data to align verse boundaries

## Next Steps

1. **Download actual Greek text files** from GitHub repositories
2. **Improve Hebrew verse parsing** - explore WLC repository for structured data
3. **Add lexicon files** for Strong's number and semantic domain tagging
4. **Enhance verse detection** with book-specific patterns
5. **Add cross-references** and parallel passage links
6. **Create embedding pipeline** to generate semantic vectors

## Troubleshooting

**Issue: "PyMuPDF not installed"**
- Run: `pip install PyMuPDF`

**Issue: Only extracting headers/footers from PDFs**
- The PDFs may have complex layouts
- Try extracting specific page ranges
- Consider using OCR tools like Tesseract for better text extraction

**Issue: No verse markers detected**
- Check if text files have standard verse format (Book Chapter:Verse)
- Hebrew/Aramaic texts may use different numbering systems
- Current fallback: paragraph-level chunking

**Issue: Text encoding issues**
- Ensure UTF-8 encoding for all text files
- Hebrew/Greek characters should display correctly
- Check console output for encoding warnings

## Resources

- [Westminster Leningrad Codex GitHub](https://github.com/cmerwich/tfbible)
- [LXX Rahlfs 1935 GitHub](https://github.com/eliranwong/LXX-Rahlfs-1935)
- [SBLGNT GitHub](https://github.com/Faithlife/SBLGNT)
- [Strong's Concordance](https://www.blueletterbible.org/lexicons/)
