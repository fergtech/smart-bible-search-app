"""
Strong's Concordance word-study lookup.

Provides English-word -> Strong's number enrichment for the KJV corpus,
built by download_strongs_lexicon.py from the real OpenScriptures Strong's
Hebrew/Greek dictionaries (public domain, James Strong 1890/1894). The
reverse index maps English KJV translation words to the Hebrew/Greek words
Strong originally assigned them to, since the app's search corpus is
English KJV text, not the original languages.

This is a best-effort join (kjv_def glosses are many-to-many with original
words), not a fully-tagged word-by-word Strong's Bible. It's meant to give
the commentary LLM real word-origin context it doesn't otherwise have.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

if config.BASE_DIR.parent == Path("/"):
    STRONGS_DIR = config.BASE_DIR / "strongs_data"
else:
    STRONGS_DIR = config.DATA_DIR / "strongs_data"

_INDEX_FILE = STRONGS_DIR / "kjv_word_index.json"

_STOP_WORDS = {
    'the', 'and', 'of', 'to', 'a', 'in', 'that', 'is', 'was', 'for',
    'with', 'as', 'his', 'he', 'be', 'not', 'by', 'but', 'from', 'they',
    'which', 'this', 'or', 'an', 'had', 'on', 'are', 'were', 'their',
    'have', 'you', 'shall', 'it', 'at', 'unto', 'thy', 'thee', 'him',
    'said', 'all', 'will', 'them', 'there', 'when', 'so', 'what', 'her',
    'she', 'ye', 'thou', 'hath', 'upon', 'into', 'unto', 'also', 'even',
}

_WORD_RE = re.compile(r"[a-z]+")

_index_cache = None

_NT_BOOKS = {
    'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans', '1 Corinthians',
    '2 Corinthians', 'Galatians', 'Ephesians', 'Philippians', 'Colossians',
    '1 Thessalonians', '2 Thessalonians', '1 Timothy', '2 Timothy', 'Titus',
    'Philemon', 'Hebrews', 'James', '1 Peter', '2 Peter', '1 John', '2 John',
    '3 John', 'Jude', 'Revelation',
}


def _testament_prefix(book: str) -> str:
    """'G' for New Testament books (originally written in Greek), 'H' for
    Old Testament (Hebrew/Aramaic) - stops a Hebrew word from being cited
    for a New Testament verse or vice versa. Confirmed live: John 3:16 (a
    Greek text) was citing H158 and H2465, genuine Hebrew Strong's entries,
    purely because Hebrew entries are inserted first when building the
    index and get_word_studies() had no concept of which testament a verse
    actually belongs to - it just took whichever entry came first."""
    return 'G' if book in _NT_BOOKS else 'H'


def _load_index() -> Dict[str, List[Dict]]:
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    if not _INDEX_FILE.exists():
        logger.info(f"Strong's index not found at {_INDEX_FILE} (run download_strongs_lexicon.py)")
        _index_cache = {}
        return _index_cache

    with open(_INDEX_FILE, "r", encoding="utf-8") as f:
        _index_cache = json.load(f)
    logger.info(f"Loaded Strong's word index: {len(_index_cache)} entries")
    return _index_cache


_hebrew_dict_cache = None
_greek_dict_cache = None


def _load_forward_dict(testament: str) -> Dict[str, Dict]:
    """Load the raw Strong's dictionary (keyed by number, e.g. 'G25'),
    as opposed to _load_index()'s reverse (English word -> numbers) index.
    Used for direct number -> definition lookups (the clickable Strong's
    number feature), not for the word-study enrichment in get_word_studies()."""
    global _hebrew_dict_cache, _greek_dict_cache

    if testament == 'H':
        if _hebrew_dict_cache is not None:
            return _hebrew_dict_cache
        path = STRONGS_DIR / "strongs-hebrew-dictionary.json"
    else:
        if _greek_dict_cache is not None:
            return _greek_dict_cache
        path = STRONGS_DIR / "strongs-greek-dictionary.json"

    if not path.exists():
        logger.info(f"Strong's dictionary not found at {path}")
        data = {}
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    if testament == 'H':
        _hebrew_dict_cache = data
    else:
        _greek_dict_cache = data
    return data


def get_definition(strongs_number: str) -> Optional[Dict]:
    """
    Direct forward lookup by Strong's number (e.g. 'G25', 'H2580'), for the
    clickable Strong's number feature. This looks up the original
    dictionary entry directly by its number - a completely different path
    from get_word_studies(), which goes English word -> candidate numbers.
    """
    if not strongs_number:
        return None
    strongs_number = strongs_number.strip().upper()
    if not strongs_number or strongs_number[0] not in ('G', 'H'):
        return None

    data = _load_forward_dict(strongs_number[0])
    entry = data.get(strongs_number)
    if not entry:
        return None

    return {
        'strongs': strongs_number,
        'lemma': entry.get('lemma', ''),
        'xlit': entry.get('xlit', ''),
        'pronunciation': entry.get('pron', ''),
        'definition': entry.get('strongs_def', '').strip('{}'),
        'kjv_translations': entry.get('kjv_def', ''),
    }


def _stem_candidates(word: str) -> List[str]:
    """Cheap English inflection variants to try when the exact word misses."""
    candidates = [word]
    if word.endswith("ied") and len(word) > 4:
        candidates.append(word[:-3] + "y")
    if word.endswith("ies") and len(word) > 4:
        candidates.append(word[:-3] + "y")
    if word.endswith("ing") and len(word) > 5:
        candidates.append(word[:-3])
        candidates.append(word[:-3] + "e")
    if word.endswith("ed") and len(word) > 4:
        candidates.append(word[:-1])   # loved -> love
        candidates.append(word[:-2])   # walked -> walk
    if word.endswith("es") and len(word) > 4:
        candidates.append(word[:-2])
    if word.endswith("s") and len(word) > 4:
        candidates.append(word[:-1])
    return candidates


def get_word_studies(verses: List[Dict], max_terms: int = 8) -> List[Dict]:
    """
    Pick the most frequent significant words across the given verses and
    look up their Strong's word-origin data.

    Returns a list of {word, strongs, lemma, xlit, definition} dicts,
    capped at max_terms.
    """
    index = _load_index()
    if not index:
        return []

    from collections import Counter
    counts = Counter()
    word_testaments: Dict[str, set] = {}
    for v in verses:
        prefix = _testament_prefix(v.get("book", ""))
        for word in _WORD_RE.findall(v.get("text", "").lower()):
            if len(word) >= 4 and word not in _STOP_WORDS:
                counts[word] += 1
                word_testaments.setdefault(word, set()).add(prefix)

    results = []
    seen_strongs = set()

    for word, _ in counts.most_common():
        if len(results) >= max_terms:
            break

        match = None
        for candidate in _stem_candidates(word):
            if candidate in index:
                match = index[candidate]
                break
        if not match:
            continue

        # Restrict to the testament(s) this word's source verse(s) actually
        # belong to - a Hebrew-only or Greek-only match list still exists
        # in the raw index for words that only translate one direction,
        # but citing it for the wrong testament is actively misleading, so
        # skip the word entirely rather than show a mismatched number.
        allowed_prefixes = word_testaments.get(word, {'H', 'G'})
        match = [e for e in match if e['strongs'][:1] in allowed_prefixes]
        if not match:
            continue

        # Common English words are often ambiguous (e.g. "save" as in
        # "rescue" vs. the archaic "except/but"). Show up to 4 candidates
        # per word so the LLM can pick the sense that fits the verse
        # context, rather than silently locking in a single guess.
        added_for_word = 0
        for entry in match:
            if entry["strongs"] in seen_strongs:
                continue
            seen_strongs.add(entry["strongs"])
            results.append({
                "word": word,
                "strongs": entry["strongs"],
                "lemma": entry["lemma"],
                "xlit": entry["xlit"],
                "definition": entry["definition"],
            })
            added_for_word += 1
            if added_for_word >= 4 or len(results) >= max_terms:
                break

        if len(results) >= max_terms:
            break

    return results


def format_word_studies(word_studies: List[Dict]) -> str:
    """Render word studies as a prompt-ready text block, or '' if none."""
    if not word_studies:
        return ""

    lines = ["Word Study (Strong's Concordance):"]
    for entry in word_studies:
        lines.append(
            f'- "{entry["word"]}" ({entry["strongs"]}, {entry["lemma"]} / {entry["xlit"]}): {entry["definition"]}'
        )
    return "\n".join(lines)
