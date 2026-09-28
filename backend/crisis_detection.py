"""
Crisis-language detection for self-harm / suicide risk.

Checked FIRST in the /commentary endpoint (see app_refactored.py), before
any verse retrieval or LLM call, so a crisis resource is guaranteed to
appear regardless of retrieval outcome or model behavior. Verified missing
entirely prior to this: a query like "I feel entirely hopeless and don't
want to wake up tomorrow, what does God say about this?" returned a purely
devotional response quoting comforting Psalms, with no acknowledgment of
the crisis language at all.

The response here is a FIXED template, never LLM-generated. An LLM could
minimize, ramble, or (as already observed elsewhere in this codebase with
"optional" prompt instructions - see lexicon_lookup.py, search_commentary_
corpus.py) simply not follow an instruction reliably. A safety-critical
resource can't depend on model compliance.

False positives here (flagging a query that wasn't truly a crisis) cost
almost nothing - the user still gets a compassionate, scripture-grounded
message. False negatives (missing a real crisis) are the failure mode that
actually matters, so phrase matching is written to favor recall over
precision.
"""

from typing import Dict, List

# Substring-matched against the lowercased query. Deliberately broad -
# see module docstring on why false positives are an acceptable cost here.
_CRISIS_PHRASES = [
    # suicidal ideation / intent
    "kill myself", "killing myself", "end my life", "ending my life",
    "end it all", "want to die", "wish i was dead", "wish i were dead",
    "better off dead", "rather be dead", "no reason to live",
    "no point in living", "not worth living", "give up on life",
    "ready to die", "take my own life", "suicidal", "suicide",
    # self-harm
    "hurt myself", "hurting myself", "cut myself", "cutting myself",
    "self harm", "self-harm", "self injury", "self-injury",
    # despair phrasing frequently paired with the above in real usage
    "can't go on", "cant go on",
    "can't take it anymore", "cant take it anymore",
    "don't want to wake up", "dont want to wake up",
    "don't want to be alive", "dont want to be alive",
    "no way out", "nothing left to live for", "no reason to keep going",
]

# 988 is the US Suicide & Crisis Lifeline (call or text). Crisis Text Line
# is US/Canada. This block is intentionally short, unconditional, and not
# something an LLM paraphrases - see build_crisis_response().
CRISIS_RESOURCE_TEXT = (
    "If you're in crisis or thinking about suicide, please reach out right now:\n"
    "- Call or text 988 (Suicide & Crisis Lifeline, US) - available 24/7\n"
    "- Text HOME to 741741 (Crisis Text Line, US/Canada)\n"
    "- Outside the US: https://findahelpline.com\n"
    "You matter, and there are people who want to help you through this right now."
)


def detect_crisis(query: str) -> bool:
    """Return True if the query contains self-harm/suicide crisis language."""
    if not query:
        return False
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in _CRISIS_PHRASES)


def build_crisis_response(query: str) -> Dict:
    """Fixed, non-LLM-generated response for crisis-flagged queries, shaped
    to match generate_commentary()'s normal return value so the API
    response format doesn't change for the frontend."""
    commentary = (
        f"{CRISIS_RESOURCE_TEXT}\n\n"
        "God is close to the brokenhearted (Psalm 34:18) and cares deeply "
        "about what you're going through (1 Peter 5:7). Please talk to "
        "someone today - a crisis counselor, a pastor, or someone you "
        "trust - alongside anything you find here."
    )
    verses: List[Dict] = [
        {
            'book': 'Psalms', 'chapter': 34, 'verse': 18,
            'text': 'The LORD is nigh unto them that are of a broken heart; '
                    'and saveth such as be of a contrite spirit.',
            'reference': 'Psalms 34:18', 'relevance_score': None,
        },
        {
            'book': '1 Peter', 'chapter': 5, 'verse': 7,
            'text': 'Casting all your care upon him; for he careth for you.',
            'reference': '1 Peter 5:7', 'relevance_score': None,
        },
    ]
    return {
        'commentary': commentary,
        'commentary_mode': 'crisis',
        'verses': verses,
        'verses_used': len(verses),
        'model_info': {'source': 'crisis_template', 'model': None},
    }
