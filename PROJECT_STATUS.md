# Biblical Text Processing Pipeline - Status Report

## ✓ Core Deliverables Complete

### 1. KJV Primary Corpus
**File:** `kjv_chunks.jsonl`
- **Status:** ✅ Complete
- **Verses:** 30,638 (Genesis 1:1 → Revelation 22:21)
- **Format:** JSONL (one JSON object per line)
- **Size:** 4,984.9 KB
- **Structure:**
  ```json
  {
    "book": "Genesis",
    "chapter": 1,
    "verse": 1,
    "language": "English",
    "source_file": "pg10.txt",
    "text": "In the beginning God created the heaven and the earth."
  }
  ```

### 2. Lexicon Metadata (Enrichment)
**File:** `lexicon_metadata.json`
- **Status:** ✅ Complete
- **Entries:** 14,174 Greek words
- **Source:** LXX-Rahlfs-1935 lexicon
- **Size:** 3,425.1 KB
- **Purpose:** Word meaning enrichment for queries
- **Structure:**
  ```json
  {
    "θεός": {
      "language": "Greek",
      "transliteration": "theos",
      "part_of_speech": "N [Noun]",
      "definition": "God; deity",
      "strongs_number": "G2316",
      "source": "LXX-Rahlfs-1935"
    }
  }
  ```

### 3. Original Language Texts (Supplementary)
**Files:**
- `biblical_verses_enhanced.json` - 7,939 Greek NT verses (SBLGNT)
- `biblical_verses_with_strongs.json` - Same verses with Strong's lexicon data
- `hebrew_aramaic_verses.json` - 72 Hebrew segments (encoding issues from PDF)

---

## Processing Scripts

### Core Pipeline
1. **download_kjv.py** - Downloads KJV from Project Gutenberg
2. **parse_kjv_simple.py** - Extracts 30,638 KJV verses into JSONL
3. **create_lexicon_metadata.json** - Builds Greek lexicon metadata

### Supplementary
- **preprocess_enhanced.py** - Processes SBLGNT Greek NT
- **integrate_strongs.py** - Adds Strong's lexicon to verses
- **extract_hebrew_aramaic.py** - PDF extraction (limited success)

---

## Data Architecture

```
book-intel/
├── kjv_chunks.jsonl              # PRIMARY: 30,638 KJV verses
├── lexicon_metadata.json          # ENRICHMENT: 14,174 Greek words
├── biblical_verses_enhanced.json  # OPTIONAL: Greek NT
├── biblical_verses_with_strongs.json  # OPTIONAL: Greek NT + lexicon
├── pg10.txt                       # Source: KJV from Gutenberg
├── sblgnt_data/                   # Source: 27 Greek NT books
└── lxx_data/                      # Source: Greek OT lexicon CSV

```

---

## Usage Guidelines

### 1. Semantic Search / Embeddings
- Use `kjv_chunks.jsonl` as primary corpus
- Each line is a complete JSON object (verse)
- Ready for sentence-transformers embedding

### 2. Word Meaning Queries
- Reference `lexicon_metadata.json` when user asks about word meanings
- Maps Greek words → transliteration, definition, Strong's number
- DO NOT attempt to translate; use for enrichment only

### 3. Cross-Reference with Original Languages
- Greek NT verses available in `biblical_verses_enhanced.json`
- Can align by book/chapter/verse with KJV
- Hebrew/Aramaic data incomplete (PDF extraction issues)

---

## Next Steps (Optional Enhancements)

### Immediate
- ✅ KJV corpus complete and ready
- ✅ Lexicon metadata available for enrichment
- ⏳ Generate embeddings using sentence-transformers
- ⏳ Build semantic search index

### Future
- 📋 Add cross-reference data (TSK, NET Bible notes)
- 📋 Parse Greek OT from `lxx_data/text_accented.csv` (623K words)
- 📋 Find structured Hebrew OT source (not PDF)
- 📋 Complete Strong's lexicon (currently 14.9% coverage)

---

## Key Design Decisions

1. **KJV as Foundation**
   - Most complete corpus (30,638 verses)
   - Clean verse structure
   - No translation ambiguity

2. **Lexicons as Enrichment**
   - Separate file for word meanings
   - Not embedded in verse text
   - Referenced on-demand for queries

3. **Original Texts as Optional**
   - Greek NT fully extracted
   - Hebrew/Aramaic incomplete
   - Can be improved independently

---

## Files Ready for Next Phase

✅ `kjv_chunks.jsonl` - Feed to embedding model
✅ `lexicon_metadata.json` - Query enrichment database
✅ Original texts - Cross-reference when needed

**All UTF-8 encoded, properly structured, ready for semantic search pipeline.**
