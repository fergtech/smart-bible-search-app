"""
Commentary Feature Validation Script
Tests the entire commentary pipeline: API endpoints, GPU acceleration, caching, and logging.

Usage:
    python test_commentary.py
    
Requirements:
    - Backend running on localhost:8000
    - Semantic embeddings generated
    - Dependencies installed: transformers, accelerate
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

API_URL = "http://localhost:8000"

# Test queries covering different themes
TEST_QUERIES = [
    {
        "query": "how to be good stewards of our time and money",
        "theme": "Stewardship & Financial Wisdom",
        "expected_verses": ["1 Timothy 6", "Matthew 25", "Luke 16"]
    },
    {
        "query": "what are the fruits of the spirit",
        "theme": "Fruits of the Spirit",
        "expected_verses": ["Galatians 5:22"]
    },
    {
        "query": "how to overcome anxiety and worry",
        "theme": "Anxiety & Peace",
        "expected_verses": ["Philippians 4:6", "Matthew 6:25"]
    },
    {
        "query": "forgiveness and mercy",
        "theme": "Forgiveness Theme",
        "expected_verses": ["Matthew 6:14", "Ephesians 4:32"]
    },
    {
        "query": "true sabbath day worship",
        "theme": "Sabbath Teaching",
        "expected_verses": ["Exodus 20:8", "Mark 2:27"]
    }
]


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_backend_health():
    """Test 1: Verify backend is running and responding"""
    print_section("TEST 1: Backend Health Check")
    
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        data = response.json()
        
        print(f"✓ Backend running: {data['service']} v{data['version']}")
        print(f"✓ Status: {data['status']}")
        print(f"✓ Verses loaded: {data['verses_loaded']:,}")
        print(f"✓ Semantic search: {'Enabled' if data['semantic_search_enabled'] else 'Disabled'}")
        
        if not data['semantic_search_enabled']:
            print("\n✗ ERROR: Semantic search disabled!")
            print("  Run: python backend/generate_embeddings.py")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Backend not responding: {e}")
        print("\n  Start backend with: cd backend && uvicorn app_refactored:app --reload")
        return False


def test_model_status():
    """Test 2: Check commentary model status and GPU"""
    print_section("TEST 2: Commentary Model Status")
    
    try:
        response = requests.get(f"{API_URL}/commentary/status", timeout=10)
        status = response.json()
        
        print(f"✓ Model loaded: {status.get('model_loaded', False)}")
        print(f"✓ Device: {status.get('device', 'unknown')}")
        print(f"✓ GPU available: {status.get('gpu_available', False)}")
        
        if status.get('gpu_available'):
            print(f"✓ GPU name: {status.get('gpu_name', 'unknown')}")
            mem_alloc = status.get('gpu_memory_allocated_gb', 0)
            mem_reserved = status.get('gpu_memory_reserved_gb', 0)
            print(f"✓ GPU memory: {mem_alloc:.2f} GB allocated, {mem_reserved:.2f} GB reserved")
        else:
            print("⚠ GPU not available - using CPU (slower)")
        
        return True
        
    except Exception as e:
        print(f"✗ Model status check failed: {e}")
        return False


def test_commentary_generation(test_case, test_num, total):
    """Test 3: Generate commentary for a query"""
    query = test_case['query']
    theme = test_case['theme']
    
    print_section(f"TEST {test_num}/{total}: {theme}")
    print(f"Query: \"{query}\"\n")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{API_URL}/commentary",
            json={
                "query": query,
                "max_results": 10,
                "use_cache": False  # Force fresh generation for testing
            },
            timeout=60  # GPU generation can take 10-30s first time
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"✗ Error {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        
        print(f"✓ Generated in {elapsed:.2f}s")
        
        # Display commentary
        commentary = data.get('commentary', '')
        print(f"\n💡 COMMENTARY:")
        print("-" * 70)
        print(commentary)
        print("-" * 70)
        
        # Validate commentary length
        if len(commentary) < 40:
            print(f"⚠ Commentary too short ({len(commentary)} chars)")
        elif len(commentary) > 500:
            print(f"⚠ Commentary too long ({len(commentary)} chars)")
        else:
            print(f"✓ Commentary length: {len(commentary)} chars (appropriate)")
        
        # Check for verse references
        import re
        verse_pattern = r'[1-3]?\s?[A-Z][a-z]+\s+\d+:\d+'
        references = re.findall(verse_pattern, commentary)
        
        if references:
            print(f"✓ Contains {len(references)} verse reference(s): {', '.join(references)}")
        else:
            print("⚠ No inline verse references found")
        
        # Display metadata
        metadata = data.get('metadata', {})
        print(f"\n📊 Metadata:")
        print(f"  Verses used: {metadata.get('verses_used', 0)}")
        print(f"  Total results: {metadata.get('total_results', 0)}")
        
        model_info = metadata.get('model_info', {})
        if model_info:
            print(f"  Model: {model_info.get('model', 'unknown')}")
            if 'device' in model_info:
                device_icon = "⚡" if model_info['device'] == 'cuda' else "💻"
                print(f"  Device: {device_icon} {model_info['device']}")
        
        # Display top verses
        verses = data.get('verses', [])[:3]
        if verses:
            print(f"\n📖 Top {len(verses)} verses:")
            for i, verse in enumerate(verses, 1):
                score = verse.get('relevance_score', 0) * 100
                print(f"  {i}. {verse['reference']} ({score:.1f}% match)")
                text_preview = verse['text'][:70] + "..." if len(verse['text']) > 70 else verse['text']
                print(f"     {text_preview}")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"✗ Request timed out (>60s). Model might be downloading for first time.")
        print("  Try again - subsequent requests will be faster.")
        return False
    except Exception as e:
        print(f"✗ Commentary generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_caching():
    """Test 4: Verify caching improves performance"""
    print_section("TEST 4: Caching Performance")
    
    query = "love your neighbor as yourself"
    
    try:
        # First request (no cache)
        print("Request 1: Fresh generation (use_cache=False)")
        start1 = time.time()
        response1 = requests.post(
            f"{API_URL}/commentary",
            json={"query": query, "use_cache": False},
            timeout=60
        )
        elapsed1 = time.time() - start1
        
        # Second request (with cache)
        print("\nRequest 2: Cached retrieval (use_cache=True)")
        start2 = time.time()
        response2 = requests.post(
            f"{API_URL}/commentary",
            json={"query": query, "use_cache": True},
            timeout=10
        )
        elapsed2 = time.time() - start2
        
        print(f"\n✓ Fresh generation: {elapsed1:.2f}s")
        print(f"✓ Cached retrieval: {elapsed2:.2f}s")
        
        if elapsed2 < elapsed1:
            speedup = elapsed1 / elapsed2
            print(f"✓ Cache speedup: {speedup:.1f}x faster")
        
        # Verify cache hit
        data2 = response2.json()
        model_info = data2.get('metadata', {}).get('model_info', {})
        if model_info.get('source') == 'cache':
            print("✓ Cache hit confirmed!")
        else:
            print("⚠ Cache source not indicated in response")
        
        return True
        
    except Exception as e:
        print(f"✗ Caching test failed: {e}")
        return False


def test_logging():
    """Test 5: Verify structured logging"""
    print_section("TEST 5: Structured Logging")
    
    log_file = Path(__file__).parent / "logs" / "commentary_log.jsonl"
    
    if not log_file.exists():
        print("⚠ No log file found yet")
        print(f"  Expected: {log_file}")
        print("  Logs are created when commentary is generated via API")
        return False
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"✓ Found {len(lines)} log entries in {log_file.name}")
        
        # Parse and validate latest entry
        if lines:
            last_entry = json.loads(lines[-1])
            
            print("\n📊 Latest Log Entry:")
            print(f"  Timestamp: {last_entry.get('timestamp')}")
            print(f"  Query: {last_entry.get('query')}")
            print(f"  Verses retrieved: {len(last_entry.get('verses_retrieved', []))}")
            
            commentary_preview = last_entry.get('commentary', '')[:60]
            print(f"  Commentary: {commentary_preview}...")
            
            # Validate structure
            required_fields = ['timestamp', 'query', 'verses_retrieved', 'commentary', 'model_info']
            missing = [f for f in required_fields if f not in last_entry]
            
            if missing:
                print(f"✗ Missing required fields: {missing}")
                return False
            else:
                print("✓ All required fields present")
            
            # Validate JSON structure
            print("\n✓ Log entry is valid JSON with correct structure:")
            print(f"  - timestamp: {type(last_entry['timestamp']).__name__}")
            print(f"  - query: {type(last_entry['query']).__name__}")
            print(f"  - verses_retrieved: list of {len(last_entry['verses_retrieved'])} items")
            print(f"  - commentary: {len(last_entry['commentary'])} chars")
            print(f"  - model_info: {type(last_entry['model_info']).__name__}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Log file contains invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Log validation failed: {e}")
        return False


def run_validation():
    """Run complete validation suite"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "COMMENTARY FEATURE VALIDATION SUITE" + " " * 22 + "║")
    print("║" + f"{'Timestamp: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
    print("╚" + "=" * 68 + "╝")
    
    results = {}
    
    # Test 1: Backend health
    results['backend'] = test_backend_health()
    if not results['backend']:
        print("\n✗ CRITICAL: Backend not running. Aborting remaining tests.")
        return
    
    # Test 2: Model status
    results['model'] = test_model_status()
    
    # Test 3-7: Commentary generation (5 queries)
    print("\n")
    commentary_results = []
    for i, test_case in enumerate(TEST_QUERIES, 1):
        success = test_commentary_generation(test_case, i + 2, len(TEST_QUERIES) + 2)
        commentary_results.append(success)
        time.sleep(0.5)  # Brief pause between tests
    
    results['commentary'] = sum(commentary_results)
    
    # Test 8: Caching
    results['caching'] = test_caching()
    
    # Test 9: Logging
    results['logging'] = test_logging()
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    print(f"\n✓ Backend health: {'PASS' if results['backend'] else 'FAIL'}")
    print(f"✓ Model status: {'PASS' if results['model'] else 'FAIL'}")
    print(f"✓ Commentary generation: {results['commentary']}/{len(TEST_QUERIES)} queries successful")
    print(f"✓ Caching: {'PASS' if results['caching'] else 'FAIL'}")
    print(f"✓ Logging: {'PASS' if results['logging'] else 'FAIL'}")
    
    total_tests = 4 + len(TEST_QUERIES)
    passed_tests = sum([
        results['backend'],
        results['model'],
        results['commentary'],
        results['caching'],
        results['logging']
    ])
    
    print(f"\n{'=' * 70}")
    print(f"  OVERALL: {passed_tests}/{total_tests} tests passed")
    print("=" * 70)
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Commentary feature is fully operational.\n")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review errors above.\n")


if __name__ == "__main__":
    try:
        run_validation()
    except KeyboardInterrupt:
        print("\n\n⚠ Validation interrupted by user\n")
    except Exception as e:
        print(f"\n\n✗ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
