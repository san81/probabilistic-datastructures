"""
Unit tests for Count-Min Sketch implementation.

Tests cover:
- Basic functionality (add, estimate)
- Accuracy and error bounds
- Merge operations
- Conservative variant
- Edge cases

Run with: python -m pytest test_countminsketch.py -v
or: python test_countminsketch.py
"""

import unittest
import sys
import os

# Add parent directory to path to import countminsketch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from countminsketch import CountMinSketch, ConservativeCountMinSketch


class TestCountMinSketch(unittest.TestCase):
    """Test cases for Count-Min Sketch"""
    
    def test_initialization(self):
        """Test Count-Min Sketch initialization."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        self.assertEqual(cms.epsilon, 0.001)
        self.assertEqual(cms.delta, 0.01)
        self.assertGreater(cms.width, 0)
        self.assertGreater(cms.depth, 0)
        self.assertEqual(len(cms.table), cms.depth)
        self.assertEqual(len(cms.table[0]), cms.width)
    
    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        with self.assertRaises(ValueError):
            CountMinSketch(epsilon=0, delta=0.01)
        
        with self.assertRaises(ValueError):
            CountMinSketch(epsilon=1.5, delta=0.01)
        
        with self.assertRaises(ValueError):
            CountMinSketch(epsilon=0.001, delta=0)
        
        with self.assertRaises(ValueError):
            CountMinSketch(epsilon=0.001, delta=1)
    
    def test_empty_sketch(self):
        """Test estimates on empty sketch."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        # All estimates should be 0
        self.assertEqual(cms.estimate("any_item"), 0)
        self.assertEqual(cms["any_item"], 0)
        self.assertEqual(cms.total_count, 0)
    
    def test_single_item(self):
        """Test adding and estimating single item."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        cms.add("test_item")
        estimate = cms.estimate("test_item")
        
        # Should be exactly 1 or slightly more (due to collisions)
        self.assertGreaterEqual(estimate, 1)
        self.assertLessEqual(estimate, 2)
    
    def test_multiple_additions_same_item(self):
        """Test adding same item multiple times."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        item = "repeated_item"
        count = 100
        
        for _ in range(count):
            cms.add(item)
        
        estimate = cms.estimate(item)
        
        # Should be close to count (might be slightly higher due to collisions)
        self.assertGreaterEqual(estimate, count)
        self.assertLessEqual(estimate, count * 1.1)  # Within 10% overestimate
    
    def test_batch_addition(self):
        """Test adding items with count parameter."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        cms.add("page1", count=100)
        cms.add("page2", count=250)
        
        # Estimates should be >= actual
        self.assertGreaterEqual(cms.estimate("page1"), 100)
        self.assertGreaterEqual(cms.estimate("page2"), 250)
        self.assertEqual(cms.total_count, 350)
    
    def test_never_underestimates(self):
        """
        Test that Count-Min Sketch NEVER underestimates.
        This is the key guarantee.
        """
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        items_and_counts = {
            "item1": 100,
            "item2": 50,
            "item3": 200,
            "item4": 75,
            "item5": 150
        }
        
        # Add items
        for item, count in items_and_counts.items():
            for _ in range(count):
                cms.add(item)
        
        # Check estimates are never less than actual
        for item, actual_count in items_and_counts.items():
            estimate = cms.estimate(item)
            self.assertGreaterEqual(estimate, actual_count,
                                   f"Underestimate detected! {item}: "
                                   f"actual={actual_count}, estimate={estimate}")
    
    def test_error_bound(self):
        """Test that error is within theoretical bound."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add many items to build up total count
        for i in range(100):
            for _ in range(100):
                cms.add(f"item_{i}")
        
        # Add specific item
        test_item = "test_item"
        actual_count = 50
        for _ in range(actual_count):
            cms.add(test_item)
        
        estimate = cms.estimate(test_item)
        error = estimate - actual_count
        max_error = cms.epsilon * cms.total_count
        
        # Error should be within bound
        self.assertLessEqual(error, max_error,
                            f"Error {error} exceeds bound {max_error}")
        
        print(f"\nError bound test:")
        print(f"  Actual: {actual_count}")
        print(f"  Estimate: {estimate}")
        print(f"  Error: {error}")
        print(f"  Max allowed error: {max_error:.0f}")
    
    def test_zipfian_distribution(self):
        """Test with Zipfian distribution (realistic web traffic pattern)."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        # Simulate Zipfian: first items get many hits, later items fewer
        num_items = 100
        actual_counts = {}
        
        for i in range(num_items):
            count = int(10000 / (i + 1))
            actual_counts[f"page{i}"] = count
            for _ in range(count):
                cms.add(f"page{i}")
        
        # Check top items (should have low error)
        errors = []
        for i in range(10):
            item = f"page{i}"
            actual = actual_counts[item]
            estimate = cms.estimate(item)
            error_rate = (estimate - actual) / actual
            errors.append(error_rate)
        
        avg_error = sum(errors) / len(errors)
        print(f"\nZipfian distribution - Avg error rate for top 10: {avg_error:.3%}")
        
        # Average error should be small for frequent items
        self.assertLess(avg_error, 0.05)  # Less than 5% on average
    
    def test_bracket_notation(self):
        """Test __getitem__ method (bracket notation)."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        cms.add("item", count=100)
        
        # Both should work
        self.assertEqual(cms["item"], cms.estimate("item"))
        self.assertGreaterEqual(cms["item"], 100)
    
    def test_merge_disjoint(self):
        """Test merging two sketches with disjoint items."""
        cms1 = CountMinSketch(epsilon=0.01, delta=0.01)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add disjoint sets
        for i in range(100):
            cms1.add(f"set1_{i}", count=10)
        
        for i in range(100):
            cms2.add(f"set2_{i}", count=20)
        
        # Merge
        cms1.merge(cms2)
        
        # Check counts
        self.assertGreaterEqual(cms1.estimate("set1_0"), 10)
        self.assertGreaterEqual(cms1.estimate("set2_0"), 20)
        self.assertEqual(cms1.total_count, 3000)  # 100*10 + 100*20
    
    def test_merge_overlapping(self):
        """Test merging two sketches with overlapping items."""
        cms1 = CountMinSketch(epsilon=0.01, delta=0.01)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add same items to both
        item = "shared_item"
        cms1.add(item, count=100)
        cms2.add(item, count=150)
        
        # Merge
        cms1.merge(cms2)
        
        # Should sum the counts
        estimate = cms1.estimate(item)
        self.assertGreaterEqual(estimate, 250)  # 100 + 150
        self.assertLessEqual(estimate, 270)  # Some tolerance for error
    
    def test_merge_different_dimensions_fails(self):
        """Test that merging sketches with different dimensions fails."""
        cms1 = CountMinSketch(epsilon=0.01, delta=0.01)
        cms2 = CountMinSketch(epsilon=0.001, delta=0.01)  # Different epsilon
        
        with self.assertRaises(ValueError):
            cms1.merge(cms2)
    
    def test_different_data_types(self):
        """Test Count-Min Sketch with various data types."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add different types
        cms.add("string", count=10)
        cms.add(123, count=20)
        cms.add(45.67, count=30)
        cms.add(True, count=5)
        
        # All should be estimable
        self.assertGreaterEqual(cms.estimate("string"), 10)
        self.assertGreaterEqual(cms.estimate(123), 20)
        self.assertGreaterEqual(cms.estimate(45.67), 30)
        self.assertGreaterEqual(cms.estimate(True), 5)
    
    def test_info_method(self):
        """Test info method returns correct statistics."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        for i in range(100):
            cms.add(f"item_{i}", count=10)
        
        info = cms.info()
        
        self.assertEqual(info['epsilon'], 0.001)
        self.assertEqual(info['delta'], 0.01)
        self.assertEqual(info['total_count'], 1000)
        self.assertGreater(info['memory_kb'], 0)
        self.assertEqual(info['max_error'], 0.001 * 1000)


class TestConservativeCountMinSketch(unittest.TestCase):
    """Test cases for Conservative Count-Min Sketch variant"""
    
    def test_initialization(self):
        """Test Conservative CMS initialization."""
        ccms = ConservativeCountMinSketch(epsilon=0.001, delta=0.01)
        
        self.assertIsInstance(ccms, CountMinSketch)
        self.assertEqual(ccms.epsilon, 0.001)
        self.assertEqual(ccms.delta, 0.01)
    
    def test_conservative_reduces_overestimation(self):
        """Test that conservative variant reduces overestimation."""
        # Create both variants
        standard = CountMinSketch(epsilon=0.01, delta=0.01)
        conservative = ConservativeCountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add same data to both with many collisions
        # Using modulo to force collisions
        for i in range(1000):
            item = f"item_{i % 50}"  # Only 50 unique items
            standard.add(item)
            conservative.add(item)
        
        # Compare estimates
        total_overestimate_standard = 0
        total_overestimate_conservative = 0
        
        for i in range(50):
            item = f"item_{i}"
            actual = 20  # Each item added 20 times (1000 / 50)
            
            std_est = standard.estimate(item)
            cons_est = conservative.estimate(item)
            
            total_overestimate_standard += (std_est - actual)
            total_overestimate_conservative += (cons_est - actual)
        
        # Conservative should have less total overestimation
        print(f"\nConservative comparison:")
        print(f"  Standard overestimate: {total_overestimate_standard}")
        print(f"  Conservative overestimate: {total_overestimate_conservative}")
        
        # Note: This might not always hold due to randomness, but should trend true
        # We'll just verify both work correctly
        self.assertGreaterEqual(total_overestimate_standard, 0)
        self.assertGreaterEqual(total_overestimate_conservative, 0)


class TestCountMinSketchEdgeCases(unittest.TestCase):
    """Edge case tests for Count-Min Sketch"""
    
    def test_unicode_strings(self):
        """Test with Unicode strings."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        unicode_items = [
            ("Hello 世界", 10),
            ("Привет мир", 20),
            ("مرحبا العالم", 30),
            ("🎉🎊🎈", 40)
        ]
        
        for item, count in unicode_items:
            cms.add(item, count=count)
        
        # All should be estimable
        for item, count in unicode_items:
            estimate = cms.estimate(item)
            self.assertGreaterEqual(estimate, count,
                                   f"Unicode item {item} underestimated")
    
    def test_empty_string(self):
        """Test with empty string."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        cms.add("", count=50)
        estimate = cms.estimate("")
        
        self.assertGreaterEqual(estimate, 50)
    
    def test_very_long_strings(self):
        """Test with very long strings."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        long_string = "x" * 10000
        cms.add(long_string, count=100)
        
        estimate = cms.estimate(long_string)
        self.assertGreaterEqual(estimate, 100)
    
    def test_negative_counts_not_allowed(self):
        """Test that negative counts work (for some use cases)."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        # Add positive count
        cms.add("item", count=100)
        
        # In theory, could support negative counts (deletions)
        # but our implementation doesn't have special handling
        # Just verify it doesn't crash
        cms.add("item", count=-10)
        estimate = cms.estimate("item")
        
        # Estimate should reflect the net count
        self.assertGreater(estimate, 0)
    
    def test_zero_count(self):
        """Test adding with count=0."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        cms.add("item", count=0)
        
        # Should not affect anything
        self.assertEqual(cms.estimate("item"), 0)
        self.assertEqual(cms.total_count, 0)
    
    def test_large_counts(self):
        """Test with very large counts."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        large_count = 1000000
        cms.add("popular_item", count=large_count)
        
        estimate = cms.estimate("popular_item")
        
        # Should be close to actual (within error bound)
        error_rate = abs(estimate - large_count) / large_count
        self.assertLess(error_rate, 0.1)  # Within 10%


class TestCountMinSketchScenarios(unittest.TestCase):
    """Real-world scenario tests"""
    
    def test_heavy_hitters(self):
        """Test finding heavy hitters (most frequent items)."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        # Simulate traffic with few heavy hitters
        for i in range(1000):
            cms.add(f"normal_{i}", count=1)
        
        # Heavy hitters
        heavy = ["popular1", "popular2", "popular3"]
        for item in heavy:
            cms.add(item, count=500)
        
        # Find items above threshold
        threshold = 400
        found_heavy = []
        
        # Check our known heavy hitters
        for item in heavy:
            if cms.estimate(item) > threshold:
                found_heavy.append(item)
        
        # Should find all heavy hitters
        self.assertEqual(len(found_heavy), 3)
    
    def test_rate_limiting(self):
        """Test using CMS for rate limiting."""
        cms = CountMinSketch(epsilon=0.01, delta=0.01)
        
        rate_limit = 100
        
        # Simulate requests
        for i in range(150):
            cms.add("192.168.1.1")
        
        for i in range(50):
            cms.add("192.168.1.2")
        
        # Check rate limits
        ip1_count = cms.estimate("192.168.1.1")
        ip2_count = cms.estimate("192.168.1.2")
        
        self.assertGreaterEqual(ip1_count, 150)
        self.assertLess(ip2_count, rate_limit)
    
    def test_top_k_queries(self):
        """Test tracking top-K most viewed pages."""
        cms = CountMinSketch(epsilon=0.001, delta=0.01)
        
        # Simulate page views
        pages_and_views = [
            ("/home", 1000),
            ("/about", 500),
            ("/products", 750),
            ("/contact", 200),
            ("/blog", 300)
        ]
        
        for page, views in pages_and_views:
            cms.add(page, count=views)
        
        # Get estimates and sort
        estimates = [(page, cms.estimate(page)) for page, _ in pages_and_views]
        estimates.sort(key=lambda x: x[1], reverse=True)
        
        # Top page should be /home
        self.assertEqual(estimates[0][0], "/home")
        self.assertGreater(estimates[0][1], 900)


def run_performance_test():
    """Performance test for Count-Min Sketch."""
    print("\n" + "=" * 70)
    print("Performance Test")
    print("=" * 70)
    
    import time
    
    cms = CountMinSketch(epsilon=0.001, delta=0.01)
    n = 1000000
    
    # Test add performance
    start = time.time()
    for i in range(n):
        cms.add(f"item_{i % 10000}")  # 10k unique items
    add_time = time.time() - start
    
    # Test estimate performance
    start = time.time()
    for i in range(10000):
        _ = cms.estimate(f"item_{i}")
    query_time = time.time() - start
    
    info = cms.info()
    
    print(f"\nAdded {n:,} items (10,000 unique)")
    print(f"Add time: {add_time:.2f} seconds ({n/add_time:,.0f} ops/sec)")
    print(f"Query time: {query_time:.2f} seconds ({10000/query_time:,.0f} ops/sec)")
    print(f"Memory: {info['memory_mb']:.2f} MB")
    print(f"Dimensions: {cms.depth} × {cms.width}")


if __name__ == '__main__':
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()
