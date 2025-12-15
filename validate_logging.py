"""
Logging Validation Script
Tests that structured logging is working correctly across all endpoints.
"""

import json
import time
from pathlib import Path
import requests
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
LOGS_DIR = Path(__file__).parent / "logs"
APP_LOG_FILE = LOGS_DIR / "app.log"

# Test queries
TEST_QUERIES = [
    {
        "query": "forgiveness",
        "endpoint": "commentary",
        "expected_fields": ["query", "commentary", "verses_count", "commentary_mode"]
    },
    {
        "query": "true sabbath day",
        "endpoint": "commentary",
        "expected_fields": ["query", "commentary", "verses_count", "commentary_mode"]
    },
    {
        "query": "how to beat addictions",
        "endpoint": "search",
        "expected_fields": ["query", "verses_count", "query_type"]
    },
    {
        "query": "love thy neighbor",
        "endpoint": "semantic_search",
        "expected_fields": ["query", "verses_count", "query_type"]
    },
    {
        "query": "faith and works",
        "endpoint": "explain",
        "expected_fields": ["verse_reference", "explanation"]
    }
]


def clear_logs():
    """Clear existing logs for clean test"""
    if APP_LOG_FILE.exists():
        APP_LOG_FILE.unlink()
        print("✓ Cleared existing logs")


def read_logs():
    """Read all log entries from app.log"""
    if not APP_LOG_FILE.exists():
        return []
    
    logs = []
    with open(APP_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    return logs


def test_search_endpoint(query, max_results=10):
    """Test /search endpoint"""
    print(f"\n[SEARCH] Testing: '{query}'")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/semantic_search",
            json={"query": query, "max_results": max_results},
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"   OK - Got {len(results)} results")
            return True
        else:
            print(f"   ERROR - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR - Exception: {e}")
        return False


def test_commentary_endpoint(query, max_results=10):
    """Test /commentary endpoint"""
    print(f"\n[COMMENTARY] Testing: '{query}'")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/commentary",
            json={"query": query, "max_results": max_results, "use_cache": False},
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Got commentary ({len(data.get('commentary', ''))} chars)")
            return True
        else:
            print(f"   ERROR - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR - Exception: {e}")
        return False


def test_explain_endpoint(query):
    """Test /explain endpoint"""
    print(f"\n[EXPLAIN] Testing: '{query}'")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/explain",
            json={"query": query, "max_results": 5, "semantic": True},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Got explanation")
            return True
        else:
            print(f"   ERROR - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR - Exception: {e}")
        return False


def test_chapter_endpoint(book="John", chapter=3):
    """Test /chapter endpoint"""
    print(f"\n[CHAPTER] Testing: {book} {chapter}")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/chapter/{book}/{chapter}",
            timeout=30
        )
        
        if response.status_code == 200:
            verses = response.json()
            print(f"   OK - Got {len(verses)} verses")
            return True
        else:
            print(f"   ERROR - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR - Exception: {e}")
        return False


def validate_log_entry(log_entry, expected_fields):
    """Validate that a log entry contains expected fields"""
    missing_fields = []
    
    for field in expected_fields:
        if field not in log_entry:
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields


def print_sample_log(log_entry):
    """Print a nicely formatted log entry sample"""
    print("\n" + "=" * 80)
    print("Sample Log Entry:")
    print("=" * 80)
    print(json.dumps(log_entry, indent=2))
    print("=" * 80)


def main():
    """Run validation tests"""
    print("\n" + "="*80)
    print("LOGGING VALIDATION TEST")
    print("="*80)
    
    # Clear logs
    clear_logs()
    
    # Test each endpoint
    print("\nRUNNING ENDPOINT TESTS")
    print("-" * 80)
    
    # Test search
    test_search_endpoint("forgiveness")
    time.sleep(1)
    
    # Test commentary
    test_commentary_endpoint("true sabbath day")
    time.sleep(2)
    
    # Test explain
    test_explain_endpoint("faith and works")
    time.sleep(1)
    
    # Test chapter
    test_chapter_endpoint("John", 3)
    time.sleep(1)
    
    # Wait for logs to be written
    print("\nWaiting for logs to be written...")
    time.sleep(2)
    
    # Read and validate logs
    print("\nVALIDATING LOG ENTRIES")
    print("-" * 80)
    
    logs = read_logs()
    
    if not logs:
        print("\nFAILED: No logs found!")
        print(f"   Expected log file: {APP_LOG_FILE}")
        return False
    
    print(f"\nOK - Found {len(logs)} log entries")
    
    # Validate structure
    validation_passed = True
    log_types = {}
    
    for i, log_entry in enumerate(logs, 1):
        event_type = log_entry.get('event_type', 'unknown')
        log_types[event_type] = log_types.get(event_type, 0) + 1
        
        # Check required fields
        required_fields = ['timestamp', 'event_type', 'session_id']
        has_required = all(field in log_entry for field in required_fields)
        
        if not has_required:
            print(f"\n   WARNING - Log entry {i} missing required fields")
            validation_passed = False
        
        # Print first log of each type as sample
        if log_types[event_type] == 1:
            print(f"\n   OK - {event_type} log structure:")
            print(f"      Fields: {', '.join(log_entry.keys())}")
    
    # Print summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    print(f"\nTotal log entries: {len(logs)}")
    print("\nLog types:")
    for log_type, count in log_types.items():
        print(f"  - {log_type}: {count}")
    
    # Show a complete sample
    if logs:
        print_sample_log(logs[0])
    
    # Final result
    print("\n" + "="*80)
    if validation_passed and len(logs) >= 4:
        print("VALIDATION PASSED")
        print(f"   - {len(logs)} log entries written")
        print(f"   - {len(log_types)} event types logged")
        print("   - All required fields present")
    else:
        print("VALIDATION FAILED")
        if len(logs) < 4:
            print(f"   - Only {len(logs)} logs found (expected at least 4)")
        if not validation_passed:
            print("   - Some log entries missing required fields")
    
    print("="*80 + "\n")
    
    return validation_passed and len(logs) >= 4


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
