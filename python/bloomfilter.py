"""
Bloom Filter: Probabilistic Set Membership Test

A space-efficient probabilistic data structure to test whether an element
is a member of a set. Allows false positives but never false negatives.

Time Complexity:
    - add(): O(k) where k = number of hash functions
    - contains(): O(k)

Space Complexity: O(m) where m = -n*ln(p)/(ln(2))^2
    Typically ~10 bits per element for 1% false positive rate

Reference:
    Bloom, "Space/time trade-offs in hash coding with allowable errors" (1970)

Author: Santhosh Gandhe
Date: 2025
"""

import hashlib
import math
from typing import Any


class BloomFilter:
    """
    Bloom Filter for fast set membership testing with configurable false positive rate.
    
    The algorithm works by:
    1. Creating a bit array of size m (all zeros initially)
    2. Using k different hash functions
    3. When adding: set k bits to 1 (at positions given by hash functions)
    4. When checking: if ALL k bits are 1, element is "probably" in set
                     if ANY bit is 0, element is "definitely not" in set
    
    Key Properties:
        - No false negatives: if it says "no", it's 100% correct
        - Configurable false positives: if it says "yes", might be wrong
        - Cannot remove elements (use Counting Bloom Filter for that)
        - Extremely space efficient (90-95% savings vs hash set)
    
    Example:
        >>> bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        >>> bf.add("user@example.com")
        >>> "user@example.com" in bf  # True
        >>> "other@example.com" in bf  # False (or 1% chance of True)
    """
    
    def __init__(self, expected_items=10000, false_positive_rate=0.01):
        """
        Initialize Bloom Filter with optimal parameters calculated automatically.
        
        Args:
            expected_items (int): Expected number of elements to store
            false_positive_rate (float): Target false positive probability (0-1)
                                        Common values: 0.01 (1%), 0.001 (0.1%)
        
        Raises:
            ValueError: If false_positive_rate not in range (0, 1)
        
        The optimal parameters are calculated using these formulas:
            - Bit array size: m = -n*ln(p) / (ln(2))^2
            - Hash functions: k = (m/n) * ln(2)
        
        Where:
            n = expected_items
            p = false_positive_rate
        
        Example sizing:
            For 1 million items with 1% FP rate:
            - Bit array: ~9.6 million bits (~1.2 MB)
            - Hash functions: 7
            - Space per item: ~9.6 bits (vs 24+ bytes in hash set)
        """
        if not 0 < false_positive_rate < 1:
            raise ValueError("False positive rate must be between 0 and 1")
        
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal bit array size using formula: m = -n*ln(p)/(ln(2))^2
        self.size = self._optimal_size(expected_items, false_positive_rate)
        
        # Calculate optimal number of hash functions using formula: k = (m/n)*ln(2)
        self.num_hashes = self._optimal_hash_count(self.size, expected_items)
        
        # Initialize bit array (using list of integers for simplicity)
        # In production, consider using bitarray library or numpy for better performance
        # and memory efficiency
        self.bit_array = [0] * self.size
        
        # Track number of items added for statistics
        self.items_added = 0
    
    @staticmethod
    def _optimal_size(n, p):
        """
        Calculate optimal bit array size to achieve target false positive rate.
        
        Formula: m = -n * ln(p) / (ln(2))^2
        
        Derivation:
            The false positive rate for a Bloom filter is: p ≈ (1 - e^(-kn/m))^k
            Solving for m to minimize p gives us this formula.
        
        Args:
            n (int): Expected number of elements
            p (float): Target false positive rate
            
        Returns:
            int: Optimal bit array size
        """
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    @staticmethod
    def _optimal_hash_count(m, n):
        """
        Calculate optimal number of hash functions.
        
        Formula: k = (m/n) * ln(2)
        
        Intuition: More hash functions → more bits set per element
                  Fewer hash functions → fewer chances to catch false positives
                  This formula finds the sweet spot that minimizes FP rate
        
        Args:
            m (int): Bit array size
            n (int): Expected number of elements
            
        Returns:
            int: Optimal number of hash functions
        """
        k = (m / n) * math.log(2)
        return int(math.ceil(k))
    
    def _hash(self, item, seed):
        """
        Generate hash value for item with given seed.
        
        Uses SHA-256 for cryptographic strength and good distribution.
        In production, consider MurmurHash3 or xxHash for speed.
        
        Args:
            item: Item to hash (converted to bytes if needed)
            seed (int): Seed value to generate different hash functions
            
        Returns:
            int: Hash value in range [0, size)
        """
        # Convert to bytes if needed
        if isinstance(item, str):
            item = item.encode('utf-8')
        elif not isinstance(item, bytes):
            item = str(item).encode('utf-8')
        
        # Create hash with seed
        h = hashlib.sha256(item + str(seed).encode()).digest()
        return int.from_bytes(h[:4], byteorder='big') % self.size
    
    def _get_positions(self, item):
        """
        Get all k bit positions for an item using double hashing.
        
        Double hashing technique: Instead of computing k independent hashes,
        we compute only 2 base hashes and generate k hashes using:
            hash_i(x) = (hash1(x) + i * hash2(x)) mod m
        
        This is more efficient while maintaining good distribution properties.
        
        Args:
            item: Item to get positions for
            
        Returns:
            list: List of k bit positions
        """
        # Generate two base hashes
        hash1 = self._hash(item, 0)
        hash2 = self._hash(item, 1)
        
        # Generate k positions using double hashing
        positions = []
        for i in range(self.num_hashes):
            # Combine the two hashes to create k different hash values
            pos = (hash1 + i * hash2) % self.size
            positions.append(pos)
        
        return positions
    
    def add(self, item):
        """
        Add an item to the Bloom filter.
        
        Sets k bits in the bit array to 1 (where k = number of hash functions).
        If bits are already 1, they stay 1 (idempotent operation).
        
        Args:
            item: Any hashable object to add
            
        Time Complexity: O(k) where k = number of hash functions
        """
        positions = self._get_positions(item)
        
        # Set all k bits to 1
        for pos in positions:
            self.bit_array[pos] = 1
        
        self.items_added += 1
    
    def contains(self, item):
        """
        Check if item might be in the set.
        
        Returns:
            bool: False = definitely NOT in set (100% certain, no false negatives)
                  True = probably in set (false positive rate = configured rate)
        
        The asymmetry is key:
            - If we return False, we're CERTAIN the item was never added
            - If we return True, there's a small chance of error (false positive)
        
        Time Complexity: O(k) where k = number of hash functions
        """
        positions = self._get_positions(item)
        
        # If ANY bit is 0, item is definitely not in set
        # If ALL bits are 1, item is probably in set
        return all(self.bit_array[pos] == 1 for pos in positions)
    
    def __contains__(self, item):
        """
        Allow 'in' operator for more Pythonic usage.
        
        Example:
            >>> if email in bloom_filter:
            ...     check_database(email)
        """
        return self.contains(item)
    
    def actual_false_positive_rate(self):
        """
        Calculate actual false positive rate based on items added so far.
        
        Formula: p ≈ (1 - e^(-kn/m))^k
        
        Where:
            k = number of hash functions
            n = number of items added
            m = bit array size
        
        This shows how FP rate increases as more items are added.
        
        Returns:
            float: Current false positive rate (0-1)
        """
        n = self.items_added
        m = self.size
        k = self.num_hashes
        
        if n == 0:
            return 0.0
        
        # Calculate probability that a bit is still 0 after n insertions
        # Then raise to power k (all k bits must be 1 for false positive)
        return (1 - math.exp(-k * n / m)) ** k
    
    def utilization(self):
        """
        Calculate percentage of bits set to 1 in the bit array.
        
        Optimal utilization is around 50% (when k is optimal).
        Much higher means filter is getting saturated (high FP rate).
        
        Returns:
            float: Percentage of bits set (0-100)
        """
        bits_set = sum(self.bit_array)
        return (bits_set / self.size) * 100
    
    def __len__(self):
        """
        Return number of items added (not unique items, as we can't know that).
        """
        return self.items_added
    
    def info(self):
        """
        Return comprehensive information about the Bloom filter.
        
        Returns:
            dict: Statistics and parameters
        """
        return {
            'size_bits': self.size,
            'size_bytes': self.size / 8,
            'size_kb': self.size / 8 / 1024,
            'num_hashes': self.num_hashes,
            'items_added': self.items_added,
            'expected_items': self.expected_items,
            'target_fp_rate': self.false_positive_rate,
            'actual_fp_rate': self.actual_false_positive_rate(),
            'utilization_percent': self.utilization()
        }


def demo():
    """
    Demonstrate Bloom Filter usage and characteristics.
    """
    print("=" * 70)
    print("Bloom Filter Demo")
    print("=" * 70)
    
    # Create Bloom filter for 10,000 items with 1% false positive rate
    bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
    
    print("\nConfiguration:")
    print(f"Expected items: {bf.expected_items:,}")
    print(f"Target false positive rate: {bf.false_positive_rate:.2%}")
    print(f"Bit array size: {bf.size:,} bits ({bf.size/8/1024:.2f} KB)")
    print(f"Number of hash functions: {bf.num_hashes}")
    
    # Add items
    print("\n" + "=" * 70)
    print("Adding 10,000 items...")
    
    items_to_add = [f"user_{i}@example.com" for i in range(10000)]
    for item in items_to_add:
        bf.add(item)
    
    print(f"Items added: {len(bf):,}")
    print(f"Actual false positive rate: {bf.actual_false_positive_rate():.4%}")
    print(f"Bit utilization: {bf.utilization():.2f}%")
    
    # Test membership
    print("\n" + "=" * 70)
    print("Testing Membership")
    
    # Test items that were added (should all return True)
    print("\nItems that WERE added (should all be True):")
    true_positives = sum(1 for item in items_to_add[:5] if item in bf)
    print(f"  Sample: {true_positives}/5")
    
    # Test items that were NOT added
    print("\nItems that were NOT added:")
    test_items = [f"new_user_{i}@example.com" for i in range(10000)]
    false_positives = sum(1 for item in test_items if item in bf)
    actual_fp_rate = false_positives / len(test_items)
    print(f"  False positives: {false_positives}/10,000 ({actual_fp_rate:.2%})")
    print(f"  Target was: {bf.false_positive_rate:.2%}")


if __name__ == "__main__":
    demo()
