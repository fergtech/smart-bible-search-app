"""
Download and Build Real Strong's Concordance Data
==================================================
Downloads the genuine Strong's Hebrew/Greek dictionaries (James Strong,
1890/1894 public domain text, OpenScriptures JSON edition) and builds a
reverse index from English KJV words to their underlying Strong's entries,
so the app can enrich commentary answers with real word-study data for the
English KJV corpus it actually searches.

This replaces the previous version of this script, which pointed at a
".json" URL that doesn't exist in the OpenScriptures repo (only ".js" is
published) and therefore always failed silently, leaving strongs_data/
empty.

Usage: python download_strongs_lexicon.py
Output (all offline afterward, no runtime network calls):
  strongs_data/strongs-hebrew-dictionary.json
  strongs_data/strongs-greek-dictionary.json
  strongs_data/kjv_word_index.json
"""

import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

SOURCES = {
    "hebrew": "https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.js",
    "greek": "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.js",
}

# Bracketed grammatical/translation notes that aren't real English words
_BRACKET_RE = re.compile(r"\[.*?\]")
_NONALPHA_RE = re.compile(r"[^a-z]+")

# Common short/function words not worth indexing even though they show up
# in kjv_def (they'd match almost every verse and add noise, not signal).
# Reflexive pronouns and generic connectives are included because Hebrew
# idiom glosses (e.g. "by one's own hand") drag them into kjv_def lists for
# words that have nothing to do with their literal English meaning.
_SKIP_WORDS = {
    "a", "an", "the", "of", "to", "in", "on", "at", "by", "or", "and",
    "be", "is", "it", "as", "so", "no", "not", "also", "up", "out",
    "from", "with", "for", "if", "his", "her", "him", "he", "she",
    "compare", "see", "used", "usually", "properly", "figuratively",
    "literally", "generally", "specifically", "including",
    "yourself", "yourselves", "himself", "herself", "itself", "myself",
    "themselves", "ourselves", "thyself", "always", "therefore",
    "together", "again", "forth", "own", "self", "one", "some", "any",
    "every", "each", "other", "another", "such", "same", "own",
}


def fetch_js_dict(url: str) -> dict:
    print(f"  Downloading {url.rsplit('/', 1)[-1]} ...")
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw = resp.read().decode("utf-8")

    # File is `var strongsXxxDictionary = { ... };` with a trailing
    # `module.exports = ...` line. Strip everything but the object literal.
    start = raw.index("{")
    end = raw.rindex("}") + 1
    obj_text = raw[start:end]
    return json.loads(obj_text)


def clean_kjv_def_words(kjv_def: str) -> list:
    """Extract plausible standalone English words from a kjv_def string."""
    text = _BRACKET_RE.sub(" ", kjv_def.lower())
    # Treat hyphens/parens/punctuation as word separators so compounds like
    # "(fore-)father(-less)" yield "father" (still imperfect, good enough
    # for a reverse-lookup enrichment layer rather than exact tagging).
    text = _NONALPHA_RE.sub(" ", text)
    words = [w for w in text.split() if len(w) >= 3 and w not in _SKIP_WORDS]
    return words


def build_reverse_index(dictionaries: dict) -> dict:
    # Keep Hebrew and Greek matches separate per word so common English
    # glosses (e.g. "love", "salvation") that hit many OT Hebrew words don't
    # crowd out the NT Greek word a commentary answer usually wants too.
    by_word = defaultdict(lambda: {"hebrew": [], "greek": []})

    for testament, entries in dictionaries.items():
        prefix = "H" if testament == "hebrew" else "G"
        for strongs_num, entry in entries.items():
            if not strongs_num.startswith(prefix):
                continue
            kjv_def = entry.get("kjv_def", "")
            if not kjv_def:
                continue
            for word in set(clean_kjv_def_words(kjv_def)):
                by_word[word][testament].append({
                    "strongs": strongs_num,
                    "lemma": entry.get("lemma", ""),
                    "xlit": entry.get("xlit", ""),
                    "definition": entry.get("strongs_def", "").strip("{}"),
                })

    # Cap noisy words that matched too many entries (e.g. very generic
    # kjv_def glosses) so lookups stay precise rather than exhaustive.
    # No further re-ranking: a common English gloss (e.g. "grace", "save")
    # often legitimately maps to several real Strong's numbers, and which
    # one fits depends on the verse it's used in. That disambiguation is
    # left to the LLM, which sees the actual verse text plus every listed
    # sense (see lexicon_lookup.get_word_studies and its prompt wiring).
    index = {}
    for word, buckets in by_word.items():
        combined = buckets["hebrew"] + buckets["greek"]
        if len(combined) > 40:
            continue
        if combined:
            index[word] = combined
    return index


def main():
    print("=" * 70)
    print("Downloading real Strong's Concordance data (OpenScriptures)")
    print("=" * 70)

    output_dir = Path("strongs_data")
    output_dir.mkdir(exist_ok=True)

    dictionaries = {}
    for testament, url in SOURCES.items():
        data = fetch_js_dict(url)
        dictionaries[testament] = data
        out_path = output_dir / f"strongs-{testament}-dictionary.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  OK: {len(data)} entries -> {out_path}")

    print("\nBuilding English KJV word -> Strong's reverse index...")
    reverse_index = build_reverse_index(dictionaries)
    index_path = output_dir / "kjv_word_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(reverse_index, f, ensure_ascii=False)
    print(f"  OK: {len(reverse_index)} indexed English words -> {index_path}")

    print("\n" + "=" * 70)
    print("Done. This data is now fully local; no network calls needed at")
    print("query time. Next: backend/lexicon_lookup.py consumes kjv_word_index.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
