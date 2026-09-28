"""
Build a searchable corpus of short theological concept documents.

Fixes the actual root cause behind the memory-similarity gap found while
testing memory_store.py: general-purpose sentence embeddings under-rate
theological synonym relationships ("sanctification" vs "becoming holy"
scored only 0.29; "trinity" vs "three persons of God" scored 0.52).
A synonym-glossary dict was considered and rejected - it only grows
forever as new phrasings show up ("being set apart", "theosis",
"Christian perfection", ...).

Concept documents fix this differently and more durably: each document's
own text naturally contains its common synonym phrasings in a real
sentence, so ANY of those phrasings shares vocabulary with the SAME
embedded chunk. This works the first time anyone asks about a concept,
not just the second time (unlike memory_store.py, which can only recall a
concept after someone already asked about it once and got it approved).

Seeded from the _THEOLOGICAL_PARADOX_PHRASES list already in
commentary_summarizer_openai.py plus other foundational terms. Not meant
to be exhaustive - see search_concept_documents.py's module docstring for
how to extend this from real usage data (memory_search log entries where
'matched' is False) rather than guessing upfront.

Output:
  concept_documents.jsonl
  cache/concept_embeddings.npy
  cache/concept_index.faiss
"""

import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

OUTPUT_JSONL = Path("concept_documents.jsonl")
CACHE_DIR = Path("cache")

# Each entry's "text" is written as natural prose specifically so common
# alternate phrasings appear as real words in the same chunk, not just as
# a bullet list a keyword-only matcher would need.
CONCEPTS = [
    {
        "concept": "Sanctification",
        "text": "Sanctification is the process of being made holy, becoming holy, or being set apart for God. It describes ongoing spiritual growth, holiness, and conformity to Christ that continues after conversion - sometimes called spiritual maturity or Christian growth. Key verses: Romans 12:1-2, 1 Peter 1:15-16, Hebrews 12:14, 1 Thessalonians 4:3, 2 Corinthians 3:18.",
    },
    {
        "concept": "Justification",
        "text": "Justification means being declared righteous or made right with God, not on the basis of one's own good works but through faith. It is a legal/positional standing before God, distinct from sanctification's ongoing process. Key verses: Romans 3:24-26, Romans 5:1, Galatians 2:16, Ephesians 2:8-9.",
    },
    {
        "concept": "Salvation",
        "text": "Salvation is deliverance from sin and its consequences, being saved, redeemed, or rescued through Jesus Christ, resulting in eternal life. It encompasses being born again and receiving forgiveness of sins. Key verses: John 3:16, Romans 10:9-10, Ephesians 2:8-9, Acts 4:12.",
    },
    {
        "concept": "Grace",
        "text": "Grace is God's unmerited favor, kindness, or gift given to people who don't deserve it - a free gift rather than something earned. It is closely tied to salvation and forgiveness. Key verses: Ephesians 2:8-9, Romans 3:24, 2 Corinthians 12:9, Titus 2:11.",
    },
    {
        "concept": "Faith",
        "text": "Faith is trust, belief, or confidence in God, often described as believing without seeing or trusting God's promises. It is the means by which salvation and grace are received. Key verses: Hebrews 11:1, Romans 10:17, Ephesians 2:8, James 2:17.",
    },
    {
        "concept": "Trinity",
        "text": "The Trinity is the doctrine that God is three persons - Father, Son, and Holy Spirit - united as one God, sometimes called the triune God or Godhead. Key verses: Matthew 28:19, 2 Corinthians 13:14, John 1:1, John 14:26.",
    },
    {
        "concept": "Atonement",
        "text": "Atonement, also called propitiation or reconciliation, is the covering or payment for sin through Christ's sacrificial death, restoring the relationship between God and humanity. Key verses: Romans 5:11, 1 John 2:2, 2 Corinthians 5:18-19, Hebrews 9:22.",
    },
    {
        "concept": "Redemption",
        "text": "Redemption means being bought back, ransomed, or delivered from slavery to sin through the price paid by Christ's blood. It is closely related to salvation and being set free. Key verses: Ephesians 1:7, Galatians 3:13, 1 Peter 1:18-19, Titus 2:14.",
    },
    {
        "concept": "Repentance",
        "text": "Repentance is turning away from sin, a change of heart and mind, godly sorrow leading to a changed life and turning back to God. Key verses: Acts 3:19, 2 Corinthians 7:10, Luke 15:7, Acts 2:38.",
    },
    {
        "concept": "Predestination",
        "text": "Predestination, also called election or God's foreordination, concerns God's sovereign choice regarding salvation, debated between Calvinism (God's sovereign choice is primary) and Arminianism (human free will to accept or reject is primary). Key verses: Ephesians 1:4-5, Romans 8:29-30, Romans 9:11-16, John 6:44.",
    },
    {
        "concept": "Eschatology",
        "text": "Eschatology is the study of end times, last things, the second coming of Christ, the rapture, tribulation, the millennium, final judgment, and the new heavens and new earth. Key verses: Revelation 20-22, Matthew 24, 1 Thessalonians 4:16-17, 2 Peter 3:10-13.",
    },
    {
        "concept": "Covenant",
        "text": "A covenant is a binding agreement or promise between God and people, such as the Abrahamic covenant, Mosaic covenant, and the new covenant established through Christ. Key verses: Genesis 15:18, Exodus 24:8, Jeremiah 31:31-34, Luke 22:20.",
    },
    {
        "concept": "Righteousness",
        "text": "Righteousness means moral uprightness, being right or just before God, or right standing with God - imputed to believers through faith in Christ rather than earned by good deeds. Key verses: Romans 3:22, 2 Corinthians 5:21, Philippians 3:9, Matthew 5:6.",
    },
    {
        "concept": "Holiness",
        "text": "Holiness is being set apart, pure, sacred, and separated from sin for God's purposes - closely tied to sanctification and reflecting God's own holy character. Key verses: 1 Peter 1:15-16, Leviticus 19:2, Hebrews 12:14, 2 Corinthians 7:1.",
    },
    {
        "concept": "Sin",
        "text": "Sin is disobedience to God, moral wrongdoing, transgression, missing the mark, or falling short of God's standard - the root cause of humanity's separation from God. Key verses: Romans 3:23, 1 John 3:4, Romans 6:23, James 4:17.",
    },
    {
        "concept": "Baptism",
        "text": "Baptism is a rite of initiation into the Christian faith symbolizing death to sin and new life in Christ, debated between infant baptism (paedobaptism) and believer's baptism (credobaptism) traditions. Key verses: Matthew 28:19, Romans 6:3-4, Acts 2:38, Colossians 2:12.",
    },
    {
        "concept": "Communion",
        "text": "Communion, also called the Lord's Supper or Eucharist, is the ordinance of bread and wine commemorating Christ's death, with different traditions holding transubstantiation, consubstantiation, or memorial views of its meaning. Key verses: 1 Corinthians 11:23-26, Luke 22:19-20, Matthew 26:26-28.",
    },
    {
        "concept": "Resurrection",
        "text": "Resurrection is being raised from the dead, most centrally Christ's resurrection from the grave, which secures believers' own future bodily resurrection and eternal life. Key verses: 1 Corinthians 15:20-22, John 11:25, Romans 6:5, 1 Corinthians 15:52-54.",
    },
    {
        "concept": "Incarnation",
        "text": "The incarnation is the doctrine that God the Son became fully human in Jesus Christ while remaining fully God - God taking on flesh, sometimes called the hypostatic union of Christ's two natures. Key verses: John 1:14, Philippians 2:6-7, Colossians 2:9, 1 Timothy 3:16.",
    },
    {
        "concept": "Kingdom of God",
        "text": "The Kingdom of God, also called the Kingdom of Heaven, refers to God's reign and rule, both a present spiritual reality and a future consummated kingdom at Christ's return. Key verses: Mark 1:15, Luke 17:21, Matthew 6:33, Revelation 11:15.",
    },
    {
        "concept": "Sabbath",
        "text": "The Sabbath is a day of rest and worship, commanded in the fourth commandment, with debate over whether it applies to Saturday, Sunday (the Lord's Day), or is fulfilled in Christ under the new covenant. Key verses: Exodus 20:8-11, Mark 2:27, Colossians 2:16-17, Hebrews 4:9-10.",
    },
    {
        "concept": "Prayer",
        "text": "Prayer is communication with God - petition, intercession, thanksgiving, confession, and worship - taught by Jesus as a central spiritual discipline. Key verses: Matthew 6:9-13, Philippians 4:6, 1 Thessalonians 5:17, James 5:16.",
    },
    {
        "concept": "Spiritual Gifts",
        "text": "Spiritual gifts are Holy-Spirit-given abilities for ministry, including gifts like tongues, prophecy, and healing, with debate between cessationism (miraculous gifts ceased after the apostolic era) and continuationism (they continue today). Key verses: 1 Corinthians 12:4-11, Romans 12:6-8, 1 Corinthians 13:8-10.",
    },
    {
        "concept": "Hell",
        "text": "Hell is the place or state of final punishment for the unrighteous, with views ranging from eternal conscious torment to annihilationism (the wicked cease to exist) to universalism (all are eventually reconciled to God). Key verses: Matthew 25:41-46, Revelation 20:14-15, 2 Thessalonians 1:9, Luke 16:23-24.",
    },
    {
        "concept": "Free Will",
        "text": "Free will concerns the extent of human freedom to choose good or evil, and to accept or reject God's offer of salvation, debated in relation to God's sovereignty and predestination. Key verses: Deuteronomy 30:19, Joshua 24:15, John 7:17, Romans 9:16.",
    },
]


def main():
    print("=" * 70)
    print("Building theological concept document corpus")
    print("=" * 70)
    print(f"Concepts: {len(CONCEPTS)}")

    entries = []
    for i, c in enumerate(CONCEPTS):
        entries.append({
            "id": f"concept_{i:03d}",
            "concept": c["concept"],
            "text": c["text"],
            "source": "Concept Glossary",
        })

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Saved -> {OUTPUT_JSONL}")

    print("\nGenerating embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [e["text"] for e in entries]
    embeddings = model.encode(texts, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    CACHE_DIR.mkdir(exist_ok=True)
    np.save(CACHE_DIR / "concept_embeddings.npy", embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(CACHE_DIR / "concept_index.faiss"))

    print(f"Saved {embeddings.shape[0]} embeddings -> cache/concept_embeddings.npy")
    print("Saved FAISS index -> cache/concept_index.faiss")

    # Sanity check against the exact failure cases from earlier testing
    print("\n" + "=" * 70)
    print("Sanity check against known embedding-gap failures:")
    print("=" * 70)
    for query in ["what does it mean to become holy", "three persons of god", "end times study"]:
        q_emb = model.encode([query], convert_to_numpy=True)
        q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
        sims = (embeddings @ q_emb[0])
        best_idx = int(sims.argmax())
        print(f"  '{query}' -> {entries[best_idx]['concept']} ({sims[best_idx]:.4f})")


if __name__ == "__main__":
    main()
