"""
Unit tests for Bloom Filter implementation.

Tests cover:
- Basic functionality (add, contains)
- False positive rates
- Different configurations
- Edge cases
- Memory efficiency

Run with: python -m pytest test_bloomfilter.py -v
or: python test_bloomfilter.py
"""

import unittest
import sys
import os

# Add parent directory to path to import bloomfilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bloomfilter import BloomFilter


class TestBloomFilter(unittest.TestCase):
    """Test cases for Bloom Filter"""
    
    def test_initialization(self):
        """Test Bloom Filter initialization."""
        bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        
        self.assertEqual(bf.expected_items, 10000)
        self.assertEqual(bf.false_positive_rate, 0.01)
        self.assertGreater(bf.size, 0)
        self.assertGreater(bf.num_hashes, 0)
        self.assertEqual(len(bf.bit_array), bf.size)
    
    def test_invalid_false_positive_rate(self):
        """Test that invalid FP rates raise errors."""
        with self.assertRaises(ValueError):
            BloomFilter(expected_items=1000, false_positive_rate=0)
        
        with self.assertRaises(ValueError):
            BloomFilter(expected_items=1000, false_positive_rate=1)
        
        with self.assertRaises(ValueError):
            BloomFilter(expected_items=1000, false_positive_rate=1.5)
    
    def test_empty_filter(self):
        """Test that empty filter returns False for all queries."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        test_items = ["test1", "test2", "test3", 123, 45.67]
        
        for item in test_items:
            self.assertFalse(bf.contains(item))
            self.assertFalse(item in bf)
    
    def test_no_false_negatives(self):
        """
        Test that items added are always found (no false negatives).
        This is the critical guarantee of Bloom filters.
        """
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        items = [f"item_{i}" for i in range(1000)]
        
        # Add all items
        for item in items:
            bf.add(item)
        
        # All items should be found (no false negatives allowed!)
        for item in items:
            self.assertTrue(bf.contains(item),
                          f"False negative detected for {item}!")
            self.assertTrue(item in bf,
                          f"False negative detected for {item} using 'in' operator!")
    
    def test_false_positive_rate_small_set(self):
        """Test false positive rate with small dataset."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        # Add 1000 items
        added_items = [f"user_{i}@example.com" for i in range(1000)]
        for item in added_items:
            bf.add(item)
        
        # Test 10000 items that were NOT added
        test_items = [f"new_user_{i}@example.com" for i in range(10000)]
        false_positives = sum(1 for item in test_items if item in bf)
        
        actual_fp_rate = false_positives / len(test_items)
        
        # Should be close to configured rate (within 50% margin)
        self.assertLess(actual_fp_rate, 0.015,
                       f"FP rate {actual_fp_rate:.3%} exceeds 1.5%")
        
        print(f"\nSmall set FP rate: {actual_fp_rate:.3%} (target: 1.0%)")
    
    def test_false_positive_rate_full_capacity(self):
        """Test false positive rate at full capacity."""
        bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        
        # Add exactly the expected number of items
        for i in range(10000):
            bf.add(f"item_{i}")
        
        # Test items not in filter
        test_items = [f"test_{i}" for i in range(10000)]
        false_positives = sum(1 for item in test_items if item in bf)
        
        actual_fp_rate = false_positives / len(test_items)
        
        # Should be very close to configured rate
        self.assertLess(actual_fp_rate, 0.02,
                       f"FP rate {actual_fp_rate:.3%} exceeds 2%")
        
        print(f"Full capacity FP rate: {actual_fp_rate:.3%} (target: 1.0%)")
    
    def test_actual_false_positive_rate_calculation(self):
        """Test the mathematical FP rate calculation."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        # Initially should be 0
        self.assertEqual(bf.actual_false_positive_rate(), 0.0)
        
        # Add items
        for i in range(1000):
            bf.add(f"item_{i}")
        
        # Calculate FP rate
        calculated_rate = bf.actual_false_positive_rate()
        
        # Should be close to configured rate
        self.assertAlmostEqual(calculated_rate, 0.01, delta=0.005)
    
    def test_utilization(self):
        """Test bit array utilization."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        # Initially should be 0%
        self.assertEqual(bf.utilization(), 0.0)
        
        # Add items
        for i in range(1000):
            bf.add(f"item_{i}")
        
        util = bf.utilization()
        
        # With optimal parameters, should be around 50%
        self.assertGreater(util, 40)
        self.assertLess(util, 60)
        
        print(f"\nUtilization: {util:.2f}% (optimal ~50%)")
    
    def test_duplicate_items(self):
        """Test that adding duplicates doesn't affect membership test."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        # Add same item multiple times
        for _ in range(100):
            bf.add("duplicate")
        
        # Should still be found
        self.assertTrue("duplicate" in bf)
        
        # Items_added counter increases though
        self.assertEqual(len(bf), 100)
    
    def test_different_data_types(self):
        """Test Bloom Filter with various data types."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        test_items = [
            "string",
            123,
            456.789,
            True,
            False,
            b"bytes",
            ("tuple", "test"),
        ]
        
        # Add items
        for item in test_items:
            bf.add(item)
        
        # All should be found
        for item in test_items:
            self.assertTrue(item in bf, f"{item} not found!")
    
    def test_len_method(self):
        """Test __len__ method returns items added count."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        self.assertEqual(len(bf), 0)
        
        for i in range(100):
            bf.add(f"item_{i}")
        
        self.assertEqual(len(bf), 100)
    
    def test_info_method(self):
        """Test info method returns correct statistics."""
        bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        
        for i in range(500):
            bf.add(f"item_{i}")
        
        info = bf.info()
        
        self.assertEqual(info['expected_items'], 1000)
        self.assertEqual(info['target_fp_rate'], 0.01)
        self.assertEqual(info['items_added'], 500)
        self.assertGreater(info['size_kb'], 0)
        self.assertGreater(info['utilization_percent'], 0)
    
    def test_different_fp_rates(self):
        """Test that different FP rates give different sizes."""
        bf_1_percent = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        bf_01_percent = BloomFilter(expected_items=1000, false_positive_rate=0.001)
        bf_10_percent = BloomFilter(expected_items=1000, false_positive_rate=0.1)
        
        # Lower FP rate should require more space
        self.assertGreater(bf_01_percent.size, bf_1_percent.size)
        self.assertLess(bf_10_percent.size, bf_1_percent.size)
        
        print(f"\n10% FP: {bf_10_percent.size} bits")
        print(f"1% FP: {bf_1_percent.size} bits")
        print(f"0.1% FP: {bf_01_percent.size} bits")
    
    def test_memory_efficiency(self):
        """Test memory efficiency compared to storing actual items."""
        bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        
        items = [f"user_{i}@example.com" for i in range(10000)]
        
        for item in items:
            bf.add(item)
        
        # Calculate approximate sizes
        bf_size_kb = bf.size / 8 / 1024
        
        # Estimate set size (pointer + string overhead)
        avg_str_size = sum(len(item) for item in items[:100]) / 100
        set_size_kb = (avg_str_size + 24) * len(items) / 1024  # 24 bytes overhead per object
        
        savings = (1 - bf_size_kb / set_size_kb) * 100
        
        self.assertGreater(savings, 85,
                          f"Space savings {savings:.1f}% less than expected")
        
        print(f"\nMemory efficiency:")
        print(f"  Set: ~{set_size_kb:.1f} KB")
        print(f"  Bloom Filter: {bf_size_kb:.2f} KB")
        print(f"  Savings: {savings:.1f}%")


class TestBloomFilterEdgeCases(unittest.TestCase):
    """Edge case tests for Bloom Filter"""
    
    def test_unicode_strings(self):
        """Test with Unicode strings."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        unicode_items = [
            "Hello 世界",
            "Привет мир",
            "مرحبا العالم",
            "🎉🎊🎈",
            "Ñoño",
            "Σὲ γνωρίζω"
        ]
        
        for item in unicode_items:
            bf.add(item)
        
        # All should be found
        for item in unicode_items:
            self.assertTrue(item in bf, f"Unicode item {item} not found!")
    
    def test_empty_string(self):
        """Test with empty string."""
        bf = BloomFilter(expected_items=10, false_positive_rate=0.01)
        
        bf.add("")
        self.assertTrue("" in bf)
        self.assertFalse("not_empty" in bf)
    
    def test_very_long_strings(self):
        """Test with very long strings."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        long_strings = [("x" * 10000) + str(i) for i in range(10)]
        
        for s in long_strings:
            bf.add(s)
        
        for s in long_strings:
            self.assertTrue(s in bf)
    
    def test_overfilling(self):
        """Test behavior when adding more items than expected."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        # Add 10x expected items
        for i in range(1000):
            bf.add(f"item_{i}")
        
        # FP rate should be higher than configured
        actual_rate = bf.actual_false_positive_rate()
        
        # Should be significantly higher than target
        self.assertGreater(actual_rate, 0.01)
        
        print(f"\nOverfilled FP rate: {actual_rate:.3%} (target: 1%, filled 10x)")
    
    def test_bytes_input(self):
        """Test with bytes input."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        bf.add(b"bytes_data")
        self.assertTrue(b"bytes_data" in bf)
        self.assertFalse(b"other_bytes" in bf)
    
    def test_numeric_values(self):
        """Test with various numeric values."""
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        numbers = [0, 1, -1, 123456789, 3.14159, -2.71828, 1e10, 1e-10]
        
        for num in numbers:
            bf.add(num)
        
        for num in numbers:
            self.assertTrue(num in bf, f"Number {num} not found!")


class TestBloomFilterScenarios(unittest.TestCase):
    """Real-world scenario tests"""
    
    def test_email_deduplication(self):
        """Test using Bloom Filter for email deduplication."""
        bf = BloomFilter(expected_items=10000, false_positive_rate=0.001)
        
        # Simulate incoming emails
        seen_emails = []
        new_emails = []
        
        for i in range(5000):
            email = f"user{i}@example.com"
            bf.add(email)
            seen_emails.append(email)
        
        # Check for duplicates
        for i in range(4500, 5500):
            email = f"user{i}@example.com"
            if email not in bf:
                new_emails.append(email)
        
        # Should have found ~500 new emails (4500-4999 are duplicates)
        self.assertAlmostEqual(len(new_emails), 500, delta=50)
    
    def test_url_crawler(self):
        """Test using Bloom Filter for URL crawling."""
        visited = BloomFilter(expected_items=100000, false_positive_rate=0.01)
        
        # Simulate visiting URLs
        base_urls = [
            "https://example.com/page",
            "https://test.com/article",
            "https://sample.org/post"
        ]
        
        for i in range(1000):
            for base in base_urls:
                url = f"{base}{i}"
                visited.add(url)
        
        # Check if we should visit
        test_url = "https://example.com/page500"
        self.assertTrue(test_url in visited)  # Already visited
        
        new_url = "https://newsite.com/page1"
        self.assertFalse(new_url in visited)  # Not visited


def run_performance_test():
    """Performance test for Bloom Filter."""
    print("\n" + "=" * 70)
    print("Performance Test")
    print("=" * 70)
    
    import time
    
    bf = BloomFilter(expected_items=1000000, false_positive_rate=0.01)
    n = 1000000
    
    # Test add performance
    start = time.time()
    for i in range(n):
        bf.add(f"item_{i}")
    add_time = time.time() - start
    
    # Test query performance
    start = time.time()
    for i in range(n):
        _ = f"item_{i}" in bf
    query_time = time.time() - start
    
    print(f"\nAdded {n:,} items")
    print(f"Add time: {add_time:.2f} seconds ({n/add_time:,.0f} ops/sec)")
    print(f"Query time: {query_time:.2f} seconds ({n/query_time:,.0f} ops/sec)")
    print(f"Memory: {bf.size/8/1024/1024:.2f} MB")
    print(f"Utilization: {bf.utilization():.2f}%")
    print(f"Actual FP rate: {bf.actual_false_positive_rate():.4%}")


if __name__ == '__main__':
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()
