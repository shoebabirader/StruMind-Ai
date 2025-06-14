"""
Comprehensive test runner for StruMind backend
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from tests.test_analysis import TestAnalysisEngine
from tests.test_design import TestDesignModules
from tests.test_api import TestAPIEndpoints
from tests.test_bim import TestBIMExportImport
from tests.test_solver import TestSolverEngine


class TestRunner:
    """
    Main test runner for all StruMind tests
    """
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting StruMind Comprehensive Test Suite")
        print("=" * 60)
        
        test_suites = [
            ("Solver Engine Tests", TestSolverEngine),
            ("Analysis Engine Tests", TestAnalysisEngine),
            ("Design Module Tests", TestDesignModules),
            ("API Endpoint Tests", TestAPIEndpoints),
            ("BIM Export/Import Tests", TestBIMExportImport)
        ]
        
        for suite_name, test_class in test_suites:
            print(f"\n📋 Running {suite_name}")
            print("-" * 40)
            
            try:
                test_instance = test_class()
                results = test_instance.run_tests()
                self.test_results[suite_name] = results
                
                suite_passed = results.get('passed', 0)
                suite_failed = results.get('failed', 0)
                suite_total = suite_passed + suite_failed
                
                self.total_tests += suite_total
                self.passed_tests += suite_passed
                self.failed_tests += suite_failed
                
                print(f"✅ {suite_passed}/{suite_total} tests passed")
                if suite_failed > 0:
                    print(f"❌ {suite_failed} tests failed")
                    
            except Exception as e:
                print(f"❌ Test suite failed to run: {e}")
                self.test_results[suite_name] = {'error': str(e)}
        
        self._print_summary()
    
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 95:
                print("🎉 EXCELLENT! All systems operational")
            elif success_rate >= 80:
                print("✅ GOOD! Most systems working correctly")
            elif success_rate >= 60:
                print("⚠️  FAIR! Some issues need attention")
            else:
                print("🚨 POOR! Critical issues detected")
        
        print("\n📋 Detailed Results:")
        for suite_name, results in self.test_results.items():
            if 'error' in results:
                print(f"  {suite_name}: ERROR - {results['error']}")
            else:
                passed = results.get('passed', 0)
                failed = results.get('failed', 0)
                total = passed + failed
                print(f"  {suite_name}: {passed}/{total} passed")
        
        print("=" * 60)


if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()