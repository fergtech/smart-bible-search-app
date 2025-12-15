"""
Comprehensive Commentary System Test - Edge Cases & Curve Balls
Tests the system's robustness with challenging, unexpected queries.
"""

import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

# Challenging test queries covering various edge cases
CURVE_BALL_QUERIES = [
    # Category: Modern slang/colloquial
    ("Modern Slang", [
        "how do i stop being toxic in relationships",
        "dealing with FOMO and social media addiction",
        "is it ok to ghost someone who hurt me",
        "my crush doesn't like me back what do i do",
        "fighting with my parents all the time",
    ]),
    
    # Category: Controversial/sensitive topics
    ("Controversial", [
        "what does the bible say about abortion",
        "is being gay a sin",
        "should i divorce my abusive spouse",
        "women in ministry leadership",
        "death penalty biblical perspective",
    ]),
    
    # Category: Very specific personal situations
    ("Personal Situations", [
        "my best friend betrayed me and i want revenge",
        "i lost my job and feel like god abandoned me",
        "my teenager is doing drugs what should i do",
        "struggling with depression and suicidal thoughts",
        "my spouse is cheating on me",
    ]),
    
    # Category: Nonsensical/gibberish
    ("Nonsense/Gibberish", [
        "asdfghjkl",
        "42",
        "potato salad recipe",
        "xyzzy plugh",
        "beep boop robot noises",
    ]),
    
    # Category: Non-biblical concepts
    ("Non-Biblical", [
        "how to invest in cryptocurrency",
        "best workout routine for muscle gain",
        "quantum physics and god",
        "climate change solutions",
        "artificial intelligence ethics",
    ]),
    
    # Category: Typos and misspellings
    ("Typos/Misspellings", [
        "forgivness and mersy",
        "how to no gods will",
        "jeasus techings",
        "prairs for helth",
        "salvashun throgh fath",
    ]),
    
    # Category: Very long rambling
    ("Long Rambling", [
        "i've been struggling with depression for years and my family doesn't understand and i feel so alone and i don't know if god even hears my prayers anymore and everything feels hopeless",
        "my life is falling apart my job my marriage my health everything is going wrong and i keep praying but nothing changes and i'm starting to lose faith",
    ]),
    
    # Category: Empty/minimal
    ("Empty/Minimal", [
        "",
        "?",
        "help",
        "god",
        "a",
    ]),
    
    # Category: Contradictory/paradoxical
    ("Paradoxes", [
        "why does a loving god allow suffering",
        "can god create a stone he cannot lift",
        "if god knows the future do we have free will",
        "problem of evil explained",
        "predestination vs free will",
    ]),
    
    # Category: Pop culture references
    ("Pop Culture", [
        "what would jesus do about thanos",
        "is the force from star wars the holy spirit",
        "batman vs superman who is more christ-like",
        "lord of the rings christian symbolism",
        "harry potter witchcraft controversy",
    ]),
    
    # Category: Multiple questions in one
    ("Multiple Questions", [
        "what is love and faith and hope and how do they work together",
        "forgiveness OR revenge? mercy OR justice?",
        "is god real and if so why doesn't he show himself",
        "heaven hell purgatory which is real",
    ]),
    
    # Category: Non-English characters
    ("Non-English", [
        "perdón y gracia",
        "αγάπη",
        "שלום",
        "信仰",
        "любовь",
    ]),
    
    # Category: Theological jargon/complex
    ("Theological Complex", [
        "hypostatic union explained",
        "penal substitutionary atonement vs christus victor",
        "cessationism vs continuationism",
        "amillennialism premillennialism postmillennialism",
        "monergism vs synergism",
    ]),
    
    # Category: Offensive/testing boundaries
    ("Boundary Testing", [
        "why is god such a jerk",
        "religion is a scam prove me wrong",
        "the bible contradicts itself everywhere",
        "jesus was just a man not god",
    ]),
]


def test_query(query: str, category: str) -> dict:
    """Test a single query against the commentary endpoint."""
    
    try:
        start_time = time.time()
        
        # Get commentary
        commentary_response = requests.post(
            f"{BASE_URL}/commentary",
            json={"query": query, "max_results": 10, "use_cache": False},
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        if commentary_response.status_code != 200:
            return {
                "category": category,
                "query": query,
                "error": f"HTTP {commentary_response.status_code}",
                "success": False,
                "elapsed": elapsed
            }
        
        result = commentary_response.json()
        commentary = result.get('commentary', '')
        mode = result.get('commentary_mode', 'unknown')
        verses_count = len(result.get('verses', []))
        
        # Quality checks
        quality_checks = {
            "has_content": len(commentary) > 20,
            "not_too_long": len(commentary) < 1000,
            "has_verses": verses_count > 0,
            "mode_valid": mode in ['full', 'fallback', 'missing'],
            "reasonable_time": elapsed < 30,
        }
        
        all_passed = all(quality_checks.values())
        
        return {
            "category": category,
            "query": query,
            "success": True,
            "commentary": commentary,
            "commentary_mode": mode,
            "verses_count": verses_count,
            "elapsed": elapsed,
            "quality_checks": quality_checks,
            "all_checks_passed": all_passed
        }
        
    except requests.exceptions.Timeout:
        return {
            "category": category,
            "query": query,
            "error": "Timeout (120s)",
            "success": False,
            "elapsed": 120
        }
    except requests.exceptions.ConnectionError:
        return {
            "category": category,
            "query": query,
            "error": "Connection refused - is backend running?",
            "success": False,
            "elapsed": 0
        }
    except Exception as e:
        return {
            "category": category,
            "query": query,
            "error": str(e),
            "success": False,
            "elapsed": 0
        }


def print_result(result: dict):
    """Pretty print a test result."""
    query = result['query'][:60] + "..." if len(result['query']) > 60 else result['query']
    
    if not result['success']:
        print(f"{RED}✗{RESET} {query}")
        print(f"  Error: {result.get('error', 'Unknown')}")
        return
    
    mode = result.get('commentary_mode', 'unknown')
    elapsed = result.get('elapsed', 0)
    all_passed = result.get('all_checks_passed', False)
    
    status_icon = f"{GREEN}✓{RESET}" if all_passed else f"{YELLOW}⚠{RESET}"
    mode_color = GREEN if mode == 'full' else YELLOW if mode == 'fallback' else RED
    
    print(f"{status_icon} {query}")
    print(f"  Mode: {mode_color}{mode}{RESET} | Time: {elapsed:.1f}s | Verses: {result.get('verses_count', 0)}")
    
    commentary = result.get('commentary', '')[:150]
    if commentary:
        print(f"  {BLUE}→{RESET} {commentary}...")
    
    # Show failed checks
    failed_checks = [k for k, v in result.get('quality_checks', {}).items() if not v]
    if failed_checks:
        print(f"  {YELLOW}Failed checks: {', '.join(failed_checks)}{RESET}")


def main():
    print(f"\n{MAGENTA}{'='*70}{RESET}")
    print(f"{MAGENTA}CURVE BALL COMMENTARY SYSTEM TEST{RESET}")
    print(f"{MAGENTA}{'='*70}{RESET}\n")
    
    # Check backend availability
    try:
        health_check = requests.get(f"{BASE_URL}/", timeout=5)
        if health_check.status_code != 200:
            print(f"{RED}✗ Backend is not responding correctly{RESET}")
            return
        print(f"{GREEN}✓ Backend is running{RESET}\n")
    except:
        print(f"{RED}✗ Cannot connect to backend at {BASE_URL}{RESET}")
        print(f"  Make sure containers are running: docker-compose up -d\n")
        return
    
    total_queries = sum(len(queries) for _, queries in CURVE_BALL_QUERIES)
    print(f"Testing {total_queries} curve ball queries across {len(CURVE_BALL_QUERIES)} categories...\n")
    
    all_results = []
    stats = {
        "total": total_queries,
        "success": 0,
        "failed": 0,
        "timeout": 0,
        "full_mode": 0,
        "fallback_mode": 0,
        "missing_mode": 0,
        "quality_passed": 0,
        "by_category": {}
    }
    
    # Run tests by category
    for category, queries in CURVE_BALL_QUERIES:
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Category: {category} ({len(queries)} queries){RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        category_stats = {"total": len(queries), "success": 0, "failed": 0}
        
        for query in queries:
            result = test_query(query, category)
            all_results.append(result)
            
            print_result(result)
            
            # Update stats
            if result['success']:
                stats['success'] += 1
                category_stats['success'] += 1
                
                mode = result.get('commentary_mode', 'unknown')
                if mode == 'full':
                    stats['full_mode'] += 1
                elif mode == 'fallback':
                    stats['fallback_mode'] += 1
                elif mode == 'missing':
                    stats['missing_mode'] += 1
                
                if result.get('all_checks_passed'):
                    stats['quality_passed'] += 1
            else:
                stats['failed'] += 1
                category_stats['failed'] += 1
                
                if result.get('error') == 'Timeout (120s)':
                    stats['timeout'] += 1
            
            time.sleep(0.5)  # Brief pause between requests
        
        stats['by_category'][category] = category_stats
        print(f"\n{YELLOW}Category {category}: {category_stats['success']}/{category_stats['total']} passed{RESET}")
    
    # Final summary
    print(f"\n{MAGENTA}{'='*70}{RESET}")
    print(f"{MAGENTA}FINAL SUMMARY{RESET}")
    print(f"{MAGENTA}{'='*70}{RESET}\n")
    
    success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
    quality_rate = (stats['quality_passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    print(f"Total Queries:    {stats['total']}")
    print(f"{GREEN}Successful:       {stats['success']} ({success_rate:.1f}%){RESET}")
    print(f"{RED}Failed:           {stats['failed']}{RESET}")
    print(f"{YELLOW}Timeouts:         {stats['timeout']}{RESET}")
    print(f"\n{BLUE}Commentary Modes:{RESET}")
    print(f"  Full:           {stats['full_mode']}")
    print(f"  Fallback:       {stats['fallback_mode']}")
    print(f"  Missing:        {stats['missing_mode']}")
    print(f"\n{GREEN}Quality Checks:   {stats['quality_passed']}/{stats['total']} passed ({quality_rate:.1f}%){RESET}")
    
    # Category breakdown
    print(f"\n{BLUE}By Category:{RESET}")
    for cat, cat_stats in stats['by_category'].items():
        rate = (cat_stats['success'] / cat_stats['total'] * 100) if cat_stats['total'] > 0 else 0
        color = GREEN if rate >= 80 else YELLOW if rate >= 50 else RED
        print(f"  {cat:25} {color}{cat_stats['success']}/{cat_stats['total']} ({rate:.0f}%){RESET}")
    
    # Highlight problematic queries
    print(f"\n{RED}{'='*70}{RESET}")
    print(f"{RED}PROBLEMATIC QUERIES{RESET}")
    print(f"{RED}{'='*70}{RESET}\n")
    
    problematic = [r for r in all_results if not r['success'] or not r.get('all_checks_passed', False)]
    
    if problematic:
        for r in problematic[:20]:  # Show first 20
            query_short = r['query'][:60] + "..." if len(r['query']) > 60 else r['query']
            if not r['success']:
                print(f"{RED}✗{RESET} [{r['category']}] '{query_short}'")
                print(f"  Error: {r.get('error', 'Unknown')}\n")
            else:
                print(f"{YELLOW}⚠{RESET} [{r['category']}] '{query_short}'")
                failed = [k for k, v in r.get('quality_checks', {}).items() if not v]
                print(f"  Issues: {', '.join(failed)}\n")
        
        if len(problematic) > 20:
            print(f"{YELLOW}... and {len(problematic) - 20} more{RESET}\n")
    else:
        print(f"{GREEN}✓ No problematic queries! System is robust.{RESET}\n")
    
    # Save detailed results
    output = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "results": all_results
    }
    
    output_file = 'commentary_curveball_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{BLUE}Detailed results saved to: {output_file}{RESET}\n")
    
    # Overall verdict
    if success_rate >= 90 and quality_rate >= 80:
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}🎉 EXCELLENT! System handles curve balls very well!{RESET}")
        print(f"{GREEN}{'='*70}{RESET}\n")
    elif success_rate >= 70:
        print(f"{YELLOW}{'='*70}{RESET}")
        print(f"{YELLOW}⚠ GOOD: System is robust but has room for improvement{RESET}")
        print(f"{YELLOW}{'='*70}{RESET}\n")
    else:
        print(f"{RED}{'='*70}{RESET}")
        print(f"{RED}⚠ NEEDS WORK: System struggles with edge cases{RESET}")
        print(f"{RED}{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
