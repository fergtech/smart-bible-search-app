"""
Final Commentary System Validation
Tests the reinforced commentary system with comprehensive checks.
"""

import requests
import json
import time
from typing import Dict, List
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_QUERIES = [
    "forgiveness",
    "true sabbath day",
    "how to beat addictions",
    "faith without works",
    "love your enemies",
    "do not worry about tomorrow",
    "what is the kingdom of heaven"
]

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class CommentaryValidator:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def log(self, message: str, color: str = RESET):
        """Print colored log message"""
        print(f"{color}{message}{RESET}")
    
    def test_backend_health(self) -> bool:
        """Test 1: Backend health check"""
        self.log("\n" + "="*70, BLUE)
        self.log("TEST 1: Backend Health Check", BLUE)
        self.log("="*70, BLUE)
        
        try:
            response = requests.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                self.log("✓ Backend is running", GREEN)
                return True
            else:
                self.log(f"✗ Backend returned status {response.status_code}", RED)
                return False
        except requests.exceptions.ConnectionError:
            self.log("✗ Cannot connect to backend. Is it running?", RED)
            return False
    
    def test_model_status(self) -> Dict:
        """Test 2: Commentary model status"""
        self.log("\n" + "="*70, BLUE)
        self.log("TEST 2: Commentary Model Status", BLUE)
        self.log("="*70, BLUE)
        
        try:
            response = requests.get(f"{API_BASE_URL}/commentary/status")
            status = response.json()
            
            self.log(f"Model loaded: {status.get('model_loaded', False)}", 
                    GREEN if status.get('model_loaded') else YELLOW)
            self.log(f"Device: {status.get('device', 'unknown')}", 
                    GREEN if status.get('device') == 'cuda' else YELLOW)
            self.log(f"GPU available: {status.get('gpu_available', False)}", 
                    GREEN if status.get('gpu_available') else YELLOW)
            
            if status.get('gpu_available'):
                self.log(f"GPU: {status.get('gpu_name', 'unknown')}", GREEN)
            
            return status
        except Exception as e:
            self.log(f"✗ Failed to get model status: {e}", RED)
            return {}
    
    def test_commentary_generation(self, query: str) -> Dict:
        """Test commentary generation for a single query"""
        self.log(f"\nQuery: '{query}'", YELLOW)
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/commentary",
                json={
                    "query": query,
                    "max_results": 10,
                    "use_cache": True
                },
                timeout=120
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code != 200:
                self.log(f"✗ Request failed with status {response.status_code}", RED)
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            data = response.json()
            
            # Extract data
            commentary = data.get('commentary', '')
            commentary_mode = data.get('commentary_mode', 'unknown')
            verses = data.get('verses', [])
            metadata = data.get('metadata', {})
            
            # Validation checks
            checks = {
                "commentary_exists": len(commentary) > 0,
                "commentary_length": 50 < len(commentary) < 500,
                "verses_returned": len(verses) > 0,
                "verses_used_correct": metadata.get('verses_used', 0) > 0,
                "mode_is_full": commentary_mode == 'full',
                "references_verses": any(v['reference'].split()[0] in commentary for v in verses[:3]) if verses else False
            }
            
            # Display results
            self.log(f"  Commentary mode: {commentary_mode}", 
                    GREEN if commentary_mode == 'full' else YELLOW)
            self.log(f"  Response time: {elapsed:.2f}s", 
                    GREEN if elapsed < 10 else YELLOW)
            self.log(f"  Commentary length: {len(commentary)} chars", 
                    GREEN if checks['commentary_length'] else YELLOW)
            self.log(f"  Verses used: {metadata.get('verses_used', 0)}", 
                    GREEN if checks['verses_used_correct'] else RED)
            self.log(f"  Verses returned: {len(verses)}", 
                    GREEN if checks['verses_returned'] else RED)
            
            # Display commentary
            self.log("\n  Commentary:", BLUE)
            self.log(f"  \"{commentary}\"", RESET)
            
            # Check for verse references
            if checks['references_verses']:
                self.log("  ✓ Commentary references verses inline", GREEN)
            else:
                self.log("  ⚠ Commentary may not reference verses", YELLOW)
            
            # Overall pass/fail
            all_passed = all([
                checks['commentary_exists'],
                checks['commentary_length'],
                checks['verses_returned'],
                checks['verses_used_correct']
            ])
            
            if all_passed:
                self.log("  ✓ All checks passed", GREEN)
                self.passed += 1
            else:
                self.log("  ✗ Some checks failed", RED)
                self.failed += 1
            
            return {
                "success": all_passed,
                "commentary": commentary,
                "commentary_mode": commentary_mode,
                "checks": checks,
                "elapsed": elapsed,
                "verses_count": len(verses)
            }
            
        except requests.exceptions.Timeout:
            self.log("✗ Request timed out (>120s)", RED)
            self.failed += 1
            return {"success": False, "error": "timeout"}
        except Exception as e:
            self.log(f"✗ Error: {e}", RED)
            self.failed += 1
            return {"success": False, "error": str(e)}
    
    def test_cache_performance(self, query: str) -> Dict:
        """Test caching performance"""
        self.log(f"\nTesting cache for: '{query}'", YELLOW)
        
        # First request (should generate)
        start1 = time.time()
        response1 = requests.post(
            f"{API_BASE_URL}/commentary",
            json={"query": query, "max_results": 10, "use_cache": True}
        )
        time1 = time.time() - start1
        
        # Second request (should be cached)
        start2 = time.time()
        response2 = requests.post(
            f"{API_BASE_URL}/commentary",
            json={"query": query, "max_results": 10, "use_cache": True}
        )
        time2 = time.time() - start2
        
        speedup = time1 / time2 if time2 > 0 else 1
        
        self.log(f"  First request: {time1:.2f}s", YELLOW)
        self.log(f"  Cached request: {time2:.2f}s", YELLOW)
        self.log(f"  Speedup: {speedup:.1f}x", 
                GREEN if speedup > 5 else YELLOW)
        
        if response1.json() == response2.json():
            self.log("  ✓ Responses are identical", GREEN)
        else:
            self.log("  ⚠ Responses differ", YELLOW)
        
        return {"time1": time1, "time2": time2, "speedup": speedup}
    
    def run_all_tests(self):
        """Run complete validation suite"""
        self.log("\n" + "="*70, BLUE)
        self.log("COMMENTARY SYSTEM VALIDATION", BLUE)
        self.log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", BLUE)
        self.log("="*70, BLUE)
        
        # Test 1: Backend health
        if not self.test_backend_health():
            self.log("\n✗ Backend is not running. Aborting tests.", RED)
            return
        
        # Test 2: Model status
        model_status = self.test_model_status()
        
        # Test 3: Commentary generation for all queries
        self.log("\n" + "="*70, BLUE)
        self.log("TEST 3: Commentary Generation", BLUE)
        self.log("="*70, BLUE)
        
        for i, query in enumerate(TEST_QUERIES, 1):
            self.log(f"\n[{i}/{len(TEST_QUERIES)}] Testing query...", BLUE)
            result = self.test_commentary_generation(query)
            self.results.append({
                "query": query,
                "result": result
            })
        
        # Test 4: Cache performance
        self.log("\n" + "="*70, BLUE)
        self.log("TEST 4: Cache Performance", BLUE)
        self.log("="*70, BLUE)
        
        cache_result = self.test_cache_performance(TEST_QUERIES[0])
        
        # Summary
        self.log("\n" + "="*70, BLUE)
        self.log("VALIDATION SUMMARY", BLUE)
        self.log("="*70, BLUE)
        self.log(f"Total queries tested: {len(TEST_QUERIES)}", YELLOW)
        self.log(f"Passed: {self.passed}", GREEN)
        self.log(f"Failed: {self.failed}", RED if self.failed > 0 else GREEN)
        self.log(f"Success rate: {(self.passed / len(TEST_QUERIES) * 100):.1f}%", 
                GREEN if self.passed == len(TEST_QUERIES) else YELLOW)
        
        # Device info
        device = model_status.get('device', 'unknown')
        self.log(f"\nRunning on: {device.upper()}", 
                GREEN if device == 'cuda' else YELLOW)
        
        if self.failed == 0:
            self.log("\n✓ ALL TESTS PASSED - Commentary system is fully operational!", GREEN)
        else:
            self.log(f"\n⚠ {self.failed} test(s) failed - Review results above", YELLOW)
        
        self.log("="*70 + "\n", BLUE)
        
        # Save detailed results
        self.save_results()
    
    def save_results(self):
        """Save validation results to JSON file"""
        output_file = "commentary_validation_results.json"
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_queries": len(TEST_QUERIES),
                "passed": self.passed,
                "failed": self.failed,
                "success_rate": round(self.passed / len(TEST_QUERIES) * 100, 2)
            },
            "results": self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        self.log(f"Detailed results saved to: {output_file}", BLUE)


if __name__ == "__main__":
    validator = CommentaryValidator()
    validator.run_all_tests()
