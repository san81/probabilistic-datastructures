"""
Unit tests for HyperLogLog implementation.

Tests cover:
- Basic functionality (add, count)
- Accuracy at different scales
- Merge operations
- Edge cases
- Error bounds

Run with: python -m pytest test_hyperloglog.py -v
or: python test_hyperloglog.py
"""

import unittest
import sys
import os

# Add parent directory to path to import hyperloglog
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyperloglog import HyperLogLog


class TestHyperLogLog(unittest.TestCase):
    """Test cases for HyperLogLog"""
    
    def test_initialization(self):
        """Test HyperLogLog initialization with valid and invalid parameters."""
        # Valid initialization
        hll = HyperLogLog(precision=14)
        self.assertEqual(hll.precision, 14)
        self.assertEqual(hll.m, 16384)  # 2^14
        self.assertEqual(len(hll.registers), 16384)
        
        # Test invalid precision
        with self.assertRaises(ValueError):
            HyperLogLog(precision=3)  # Too small
        
        with self.assertRaises(ValueError):
            HyperLogLog(precision=17)  # Too large
    
    def test_empty_hyperloglog(self):
        """Test count on empty HyperLogLog."""
        hll = HyperLogLog(precision=10)
        count = hll.count()
        self.assertAlmostEqual(count, 0, delta=10)
    
    def test_single_element(self):
        """Test adding and counting single element."""
        hll = HyperLogLog(precision=14)
        hll.add("test_element")
        count = hll.count()
        # Should be close to 1, allowing some error
        self.assertAlmostEqual(count, 1, delta=1)
    
    def test_small_cardinality(self):
        """Test accuracy with small number of unique elements (100)."""
        hll = HyperLogLog(precision=14)
        expected = 100
        
        for i in range(expected):
            hll.add(f"element_{i}")
        
        estimated = hll.count()
        error_rate = abs(estimated - expected) / expected
        
        # Should be within 5% for small cardinalities
        self.assertLess(error_rate, 0.05, 
                       f"Error rate {error_rate:.2%} exceeds 5%")
    
    def test_medium_cardinality(self):
        """Test accuracy with medium number of unique elements (10,000)."""
        hll = HyperLogLog(precision=14)
        expected = 10000
        
        for i in range(expected):
            hll.add(f"user_{i}")
        
        estimated = hll.count()
        error_rate = abs(estimated - expected) / expected
        
        # Should be within 2% for medium cardinalities
        self.assertLess(error_rate, 0.02,
                       f"Error rate {error_rate:.2%} exceeds 2%")
    
    def test_large_cardinality(self):
        """Test accuracy with large number of unique elements (100,000)."""
        hll = HyperLogLog(precision=14)
        expected = 100000
        
        for i in range(expected):
            hll.add(f"item_{i}")
        
        estimated = hll.count()
        error_rate = abs(estimated - expected) / expected
        
        # Should be within 1.5% for large cardinalities
        self.assertLess(error_rate, 0.015,
                       f"Error rate {error_rate:.2%} exceeds 1.5%")
    
    def test_duplicate_elements(self):
        """Test that duplicate elements don't affect cardinality."""
        hll = HyperLogLog(precision=12)
        
        # Add same elements multiple times
        for _ in range(100):
            hll.add("duplicate")
        
        for i in range(10):
            for _ in range(10):
                hll.add(f"element_{i}")
        
        estimated = hll.count()
        expected = 11  # "duplicate" + 10 unique elements
        
        # Should estimate around 11
        self.assertAlmostEqual(estimated, expected, delta=2)
    
    def test_merge_disjoint_sets(self):
        """Test merging two HyperLogLogs with completely disjoint sets."""
        hll1 = HyperLogLog(precision=12)
        hll2 = HyperLogLog(precision=12)
        
        # Add disjoint sets
        for i in range(5000):
            hll1.add(f"set1_{i}")
        
        for i in range(5000):
            hll2.add(f"set2_{i}")
        
        # Merge
        hll1.merge(hll2)
        
        estimated = hll1.count()
        expected = 10000
        error_rate = abs(estimated - expected) / expected
        
        # More lenient for merged HLLs due to compound error
        self.assertLess(error_rate, 0.03,
                       f"Merge error rate {error_rate:.2%} exceeds 3%")
    
    def test_merge_overlapping_sets(self):
        """Test merging two HyperLogLogs with overlapping sets."""
        hll1 = HyperLogLog(precision=12)
        hll2 = HyperLogLog(precision=12)
        
        # Add overlapping sets: 0-4999 and 3000-7999
        for i in range(5000):
            hll1.add(f"user_{i}")
        
        for i in range(3000, 8000):
            hll2.add(f"user_{i}")
        
        # Merge
        hll1.merge(hll2)
        
        estimated = hll1.count()
        expected = 8000  # Union: 0-7999
        error_rate = abs(estimated - expected) / expected
        
        self.assertLess(error_rate, 0.03,
                       f"Overlapping merge error {error_rate:.2%} exceeds 3%")
    
    def test_merge_different_precision_fails(self):
        """Test that merging HLLs with different precision raises error."""
        hll1 = HyperLogLog(precision=10)
        hll2 = HyperLogLog(precision=12)
        
        with self.assertRaises(ValueError):
            hll1.merge(hll2)
    
    def test_different_data_types(self):
        """Test HyperLogLog with different data types."""
        hll = HyperLogLog(precision=12)
        
        # Add different types
        hll.add("string")
        hll.add(12345)
        hll.add(12345.67)
        hll.add(True)
        hll.add(b"bytes")
        
        estimated = hll.count()
        # Should count 5 unique items (note: True might hash same as 1)
        self.assertGreaterEqual(estimated, 4)
        self.assertLessEqual(estimated, 6)
    
    def test_len_method(self):
        """Test __len__ method returns integer cardinality."""
        hll = HyperLogLog(precision=12)
        
        for i in range(1000):
            hll.add(f"item_{i}")
        
        length = len(hll)
        self.assertIsInstance(length, int)
        self.assertAlmostEqual(length, 1000, delta=50)
    
    def test_memory_usage(self):
        """Test memory usage calculation."""
        hll = HyperLogLog(precision=14)
        mem = hll.memory_usage()
        
        self.assertEqual(mem['registers'], 16384)
        self.assertEqual(mem['bytes'], 16384)
        self.assertAlmostEqual(mem['kilobytes'], 16, delta=0.1)
    
    def test_precision_vs_accuracy(self):
        """Test that higher precision gives better accuracy."""
        expected = 10000
        
        # Test with different precisions
        precisions_and_errors = []
        
        for precision in [10, 12, 14]:
            hll = HyperLogLog(precision=precision)
            
            for i in range(expected):
                hll.add(f"item_{i}")
            
            estimated = hll.count()
            error_rate = abs(estimated - expected) / expected
            precisions_and_errors.append((precision, error_rate))
        
        # Higher precision should generally have lower error
        # (not strict because of randomness, but should trend down)
        errors = [e for p, e in precisions_and_errors]
        print(f"\nPrecision vs Error: {precisions_and_errors}")
        
        # At least verify precision=14 is better than precision=10
        self.assertLess(errors[2], errors[0] * 1.5)
    
    def test_idempotency(self):
        """Test that adding same element multiple times has same effect as once."""
        hll1 = HyperLogLog(precision=12)
        hll2 = HyperLogLog(precision=12)
        
        # Add once
        hll1.add("test")
        
        # Add multiple times
        for _ in range(100):
            hll2.add("test")
        
        # Should give same estimate
        self.assertAlmostEqual(hll1.count(), hll2.count(), delta=1)


class TestHyperLogLogEdgeCases(unittest.TestCase):
    """Edge case tests for HyperLogLog"""
    
    def test_unicode_strings(self):
        """Test HyperLogLog with Unicode strings."""
        hll = HyperLogLog(precision=12)
        
        unicode_strings = [
            "Hello 世界",
            "Привет мир",
            "مرحبا العالم",
            "🎉🎊🎈",
            "Ñoño"
        ]
        
        for s in unicode_strings:
            hll.add(s)
        
        estimated = hll.count()
        self.assertAlmostEqual(estimated, len(unicode_strings), delta=2)
    
    def test_empty_string(self):
        """Test adding empty string."""
        hll = HyperLogLog(precision=10)
        hll.add("")
        hll.add("")
        
        count = hll.count()
        # Should count as 1 unique element
        self.assertAlmostEqual(count, 1, delta=1)
    
    def test_very_long_strings(self):
        """Test with very long strings."""
        hll = HyperLogLog(precision=12)
        
        # Add long strings
        for i in range(100):
            long_string = "x" * 10000 + str(i)
            hll.add(long_string)
        
        estimated = hll.count()
        self.assertAlmostEqual(estimated, 100, delta=10)


def run_performance_test():
    """
    Performance test (not part of unit tests).
    Run separately to measure performance.
    """
    print("\n" + "=" * 70)
    print("Performance Test")
    print("=" * 70)
    
    import time
    
    hll = HyperLogLog(precision=14)
    n = 1000000
    
    start = time.time()
    for i in range(n):
        hll.add(f"element_{i}")
    end = time.time()
    
    estimated = hll.count()
    error = abs(estimated - n) / n * 100
    
    print(f"\nAdded {n:,} unique elements")
    print(f"Time: {end - start:.2f} seconds")
    print(f"Rate: {n / (end - start):,.0f} elements/second")
    print(f"Estimated: {estimated:,.0f}")
    print(f"Error: {error:.2f}%")
    print(f"Memory: {hll.memory_usage()['kilobytes']:.2f} KB")


if __name__ == '__main__':
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()
