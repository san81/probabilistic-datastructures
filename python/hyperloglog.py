"""
HyperLogLog: Probabilistic Cardinality Estimator

A space-efficient algorithm for counting distinct elements in a dataset.
Uses ~1.04/sqrt(m) relative error where m is the number of registers.

Time Complexity:
    - add(): O(1)
    - count(): O(m) where m = 2^precision
    - merge(): O(m)

Space Complexity: O(m) where m = 2^precision (typically 12-16 KB)

Reference:
    Flajolet et al., "HyperLogLog: the analysis of a near-optimal 
    cardinality estimation algorithm" (2007)

Author: Santhosh Gandhe
Date: 2025
"""

import hashlib
import math


class HyperLogLog:
    """
    HyperLogLog probabilistic cardinality estimator.
    
    The algorithm works by:
    1. Hashing each element to get random bits
    2. Using first 'precision' bits to select a bucket (register)
    3. Counting leading zeros in remaining bits
    4. Storing the maximum leading zeros seen per bucket
    5. Estimating cardinality using harmonic mean of all buckets
    
    The intuition: If you flip coins until you get heads, and it took 10 flips,
    you'd think "that's rare!" The more unique elements you see, the more likely
    you'll encounter rare events (long runs of zeros in hash values).
    
    Example:
        >>> hll = HyperLogLog(precision=14)
        >>> for i in range(100000):
        ...     hll.add(f"user_{i}")
        >>> print(f"Unique count: {hll.count()}")
        Unique count: ~100000 (±1% error)
    """
    
    def __init__(self, precision=14):
        """
        Initialize HyperLogLog with specified precision.
        
        Args:
            precision (int): Number of bits for bucketing (4-16 recommended)
                           Creates 2^precision buckets (registers)
                           Higher precision = more accuracy but more memory
                           
        Raises:
            ValueError: If precision not in range [4, 16]
            
        Precision Guide:
            - precision=10: 1024 buckets, ~1KB, ±3.2% error
            - precision=12: 4096 buckets, ~4KB, ±1.6% error
            - precision=14: 16384 buckets, ~16KB, ±0.8% error
            - precision=16: 65536 buckets, ~64KB, ±0.4% error
            
        Memory Formula: m * 6 bits (approx), where m = 2^precision
        """
        if not 4 <= precision <= 16:
            raise ValueError("Precision must be between 4 and 16")
        
        self.precision = precision
        self.m = 1 << precision  # 2^precision buckets (bit shift is faster than pow)
        
        # Each register stores the maximum number of leading zeros seen
        # Initialize all registers to 0
        self.registers = [0] * self.m
        
        # Alpha constant for bias correction
        # These values are derived empirically to minimize estimation bias
        if self.m >= 128:
            self.alpha = 0.7213 / (1 + 1.079 / self.m)
        elif self.m >= 64:
            self.alpha = 0.709
        elif self.m >= 32:
            self.alpha = 0.697
        elif self.m >= 16:
            self.alpha = 0.673
        else:
            self.alpha = 0.5
    
    def _hash(self, value):
        """
        Hash a value to 64-bit integer.
        
        Uses SHA-1 for good distribution properties. In production,
        consider using MurmurHash3 or xxHash for better performance.
        
        Args:
            value: Any value that can be converted to bytes
            
        Returns:
            int: 64-bit hash value
        """
        # Convert to bytes if needed
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            value = str(value).encode('utf-8')
        
        # Use first 8 bytes of SHA-1 hash as 64-bit int
        hash_bytes = hashlib.sha1(value).digest()[:8]
        return int.from_bytes(hash_bytes, byteorder='big')
    
    def _leading_zeros(self, bits, max_width=64):
        """
        Count leading zeros in binary representation.
        Returns position of first 1-bit (1-indexed).
        
        Example:
            bits = 0b0001010 (binary)
            Returns: 4 (three leading zeros, position of first 1 is 4)
        
        Args:
            bits (int): Integer to count leading zeros in
            max_width (int): Maximum bit width to consider
            
        Returns:
            int: Position of first 1-bit (1-indexed), or max_width if all zeros
        """
        if bits == 0:
            return max_width
        
        # Count leading zeros by checking bits from left to right
        leading = 0
        mask = 1 << (max_width - 1)  # Start with leftmost bit
        
        while (bits & mask) == 0:
            leading += 1
            mask >>= 1  # Shift right to check next bit
        
        return leading + 1  # Return 1-indexed position
    
    def add(self, value):
        """
        Add an element to the HyperLogLog.
        
        This operation:
        1. Hashes the value
        2. Uses first 'precision' bits to select bucket
        3. Counts leading zeros in remaining bits
        4. Updates bucket with maximum seen
        
        Args:
            value: Element to add (any hashable type)
            
        Time Complexity: O(1)
        """
        # Get 64-bit hash of the value
        hash_value = self._hash(value)
        
        # Extract bucket index from first 'precision' bits
        # Example: precision=14, hash_value first 14 bits determine bucket (0-16383)
        bucket_idx = hash_value & ((1 << self.precision) - 1)
        
        # Use remaining bits to count leading zeros
        # Shift right to remove the bits we used for bucket index
        remaining_bits = hash_value >> self.precision
        leading_zeros = self._leading_zeros(remaining_bits, 64 - self.precision)
        
        # Update register with maximum leading zeros seen
        # We only care about the maximum because rare events (long runs of zeros)
        # indicate we've seen many unique elements
        self.registers[bucket_idx] = max(self.registers[bucket_idx], leading_zeros)
    
    def count(self):
        """
        Estimate the cardinality (number of unique elements).
        
        Uses the harmonic mean of all bucket estimates with bias corrections
        for small and large cardinalities.
        
        Formula:
            E = alpha * m^2 / sum(2^(-M[j]))
            
        Where:
            - alpha = bias correction constant
            - m = number of buckets
            - M[j] = value in register j
            
        Returns:
            float: Estimated cardinality
            
        Time Complexity: O(m) where m = number of buckets
        """
        # Calculate raw estimate using harmonic mean
        # The harmonic mean helps average out the noise from individual buckets
        raw_estimate = self.alpha * (self.m ** 2) / sum(2 ** (-x) for x in self.registers)
        
        # Apply bias corrections for edge cases
        
        # Small range correction: when estimate is small, account for empty buckets
        if raw_estimate <= 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros != 0:
                # Use linear counting for small cardinalities
                return self.m * math.log(self.m / zeros)
        
        # Medium range: no correction needed
        if raw_estimate <= (1/30) * (1 << 32):
            return raw_estimate
        
        # Large range correction: compensate for hash collisions
        else:
            return -1 * (1 << 32) * math.log(1 - raw_estimate / (1 << 32))
    
    def merge(self, other):
        """
        Merge another HyperLogLog into this one.
        
        This is useful for distributed systems where each node maintains
        its own HLL and they need to be combined.
        
        The merge operation takes the maximum of corresponding registers,
        which maintains the HyperLogLog properties.
        
        Args:
            other (HyperLogLog): Another HyperLogLog to merge
            
        Raises:
            ValueError: If HyperLogLogs have different precision
            
        Time Complexity: O(m)
        """
        if self.precision != other.precision:
            raise ValueError("Cannot merge HyperLogLogs with different precision")
        
        # Take maximum of each corresponding register pair
        for i in range(self.m):
            self.registers[i] = max(self.registers[i], other.registers[i])
    
    def __len__(self):
        """
        Allow len() to get cardinality estimate.
        
        Example:
            >>> hll = HyperLogLog()
            >>> hll.add("item1")
            >>> len(hll)
            1
        """
        return int(self.count())
    
    def memory_usage(self):
        """
        Calculate approximate memory usage in bytes.
        
        Returns:
            dict: Memory statistics
        """
        # Each register typically needs 6 bits on average
        # For simplicity, assuming 1 byte per register
        bytes_used = self.m
        return {
            'registers': self.m,
            'bytes': bytes_used,
            'kilobytes': bytes_used / 1024,
            'megabytes': bytes_used / (1024 * 1024)
        }


def demo():
    """
    Demonstrate HyperLogLog usage and accuracy.
    """
    print("=" * 60)
    print("HyperLogLog Demo")
    print("=" * 60)
    
    # Test with different sizes
    test_sizes = [100, 1000, 10000, 100000]
    
    for size in test_sizes:
        hll = HyperLogLog(precision=14)  # ~16KB memory
        
        # Add elements
        for i in range(size):
            hll.add(f"user_{i}")
        
        estimated = hll.count()
        error = abs(estimated - size) / size * 100
        
        print(f"\nActual: {size:,}")
        print(f"Estimated: {estimated:,.0f}")
        print(f"Error: {error:.2f}%")
    
    # Demonstrate merging
    print("\n" + "=" * 60)
    print("Merge Demo")
    print("=" * 60)
    
    hll1 = HyperLogLog(precision=12)
    hll2 = HyperLogLog(precision=12)
    
    # Add different sets with overlap
    for i in range(5000):
        hll1.add(f"user_{i}")
    
    for i in range(3000, 8000):  # Overlap: 3000-4999
        hll2.add(f"user_{i}")
    
    print(f"\nHLL1 count: {hll1.count():,.0f}")
    print(f"HLL2 count: {hll2.count():,.0f}")
    
    # Merge
    hll1.merge(hll2)
    print(f"After merge: {hll1.count():,.0f}")
    print(f"Expected (union): 8,000")


if __name__ == "__main__":
    demo()
