"""
Count-Min Sketch: Probabilistic Frequency Counter

A space-efficient probabilistic data structure for estimating frequencies
of elements in a data stream. Provides approximate counts with guarantees.

Time Complexity:
    - add(): O(d) where d = depth
    - estimate(): O(d)
    - merge(): O(d * w) where w = width

Space Complexity: O(d * w) where d = ceil(ln(1/δ)), w = ceil(e/ε)

Reference:
    Cormode & Muthukrishnan, "An improved data stream summary: 
    the count-min sketch" (2005)

Author: Santhosh Gandhe
Date: 2025
"""

import hashlib
import math
from typing import Any


class CountMinSketch:
    """
    Count-Min Sketch for frequency estimation in data streams.
    
    The algorithm works by:
    1. Maintaining a 2D array (d rows × w columns) of counters
    2. Using d different hash functions (one per row)
    3. When adding item: increment counters at array[i][hash_i(item)] for all i
    4. When querying: return MINIMUM of all d counters for that item
    
    Why minimum? Hash collisions cause overestimation (multiple items map to
    same counter). Since we never decrement, the minimum counter is closest
    to the true count.
    
    Key Properties:
        - Never underestimates (always returns count >= true count)
        - Configurable error bounds: ε (error) and δ (confidence)
        - With probability ≥ (1-δ): estimate ≤ true_count + ε*total_count
        - Can be merged across distributed systems
    
    Example:
        >>> cms = CountMinSketch(epsilon=0.001, delta=0.01)
        >>> cms.add("page_view")
        >>> cms.add("page_view")
        >>> cms.estimate("page_view")  # Returns >= 2
    """
    
    def __init__(self, epsilon=0.001, delta=0.01):
        """
        Initialize Count-Min Sketch with error bounds.
        
        Args:
            epsilon (float): Error tolerance (0-1)
                           Controls width: smaller ε = wider array = better accuracy
                           Estimate error will be at most ε * total_count
            delta (float): Failure probability (0-1)
                          Controls depth: smaller δ = more rows = higher confidence
                          Error bound holds with probability (1-δ)
        
        Raises:
            ValueError: If epsilon or delta not in range (0, 1)
        
        Optimal parameters:
            - Width: w = ceil(e/ε) where e ≈ 2.718
            - Depth: d = ceil(ln(1/δ))
        
        Example configurations:
            ε=0.01, δ=0.01:  width=272, depth=5  (1% error, 99% confidence)
            ε=0.001, δ=0.01: width=2719, depth=5 (0.1% error, 99% confidence)
            ε=0.001, δ=0.001: width=2719, depth=7 (0.1% error, 99.9% confidence)
        
        Memory usage:
            Assuming 8 bytes per counter: 8 * d * w bytes
            Example: ε=0.001, δ=0.01 → ~106 KB
        """
        if not 0 < epsilon < 1:
            raise ValueError("Epsilon must be between 0 and 1")
        if not 0 < delta < 1:
            raise ValueError("Delta must be between 0 and 1")
        
        self.epsilon = epsilon
        self.delta = delta
        
        # Calculate optimal dimensions using formulas
        # Width formula: w = ceil(e/epsilon) gives us the space needed to bound error
        self.width = int(math.ceil(math.e / epsilon))
        
        # Depth formula: d = ceil(ln(1/delta)) gives us rows needed for confidence
        self.depth = int(math.ceil(math.log(1 / delta)))
        
        # Initialize counter matrix: all counters start at 0
        # In production, consider using numpy array for better performance
        self.table = [[0] * self.width for _ in range(self.depth)]
        
        # Track total count across all items for error bound calculation
        self.total_count = 0
    
    def _hash(self, item, seed):
        """
        Generate hash value for item with given seed.
        
        Each row uses a different seed to create independent hash functions.
        This independence is crucial for the probabilistic guarantees.
        
        Args:
            item: Item to hash (converted to bytes if needed)
            seed (int): Seed to create different hash function (0 to depth-1)
            
        Returns:
            int: Column index in range [0, width)
        """
        # Convert to bytes if needed
        if isinstance(item, str):
            item = item.encode('utf-8')
        elif not isinstance(item, bytes):
            item = str(item).encode('utf-8')
        
        # Create hash with seed to get different hash function per row
        h = hashlib.sha256(item + str(seed).encode()).digest()
        return int.from_bytes(h[:4], byteorder='big') % self.width
    
    def add(self, item, count=1):
        """
        Add item to the sketch (increment its count).
        
        This operation increments counters in all d rows at positions
        determined by d hash functions. Hash collisions cause multiple
        items to share counters, leading to overestimation.
        
        Args:
            item: Any hashable object
            count (int): Amount to increment (default 1)
                        Use count > 1 for batch updates or weighted items
        
        Time Complexity: O(d) where d = depth
        
        Example:
            >>> cms.add("page1")           # Increment by 1
            >>> cms.add("page1", count=5)  # Increment by 5
        """
        # Update each row with its corresponding hash function
        for i in range(self.depth):
            col = self._hash(item, i)
            self.table[i][col] += count
        
        # Track total for error bound calculation
        self.total_count += count
    
    def estimate(self, item):
        """
        Estimate the count of an item.
        
        Returns the MINIMUM count across all d hash functions.
        
        Why minimum?
            - Hash collisions cause counters to be incremented by other items
            - This only INCREASES counter values, never decreases
            - The minimum counter has likely seen the fewest collisions
            - Therefore, minimum is closest to the true count
        
        Guarantee:
            With probability ≥ (1-δ):
                true_count ≤ estimate ≤ true_count + ε*total_count
        
        Args:
            item: Item to estimate count for
            
        Returns:
            int: Estimated count (always >= true count)
            
        Time Complexity: O(d) where d = depth
        """
        counts = []
        for i in range(self.depth):
            col = self._hash(item, i)
            counts.append(self.table[i][col])
        
        # Return minimum to get best estimate
        return min(counts)
    
    def __getitem__(self, item):
        """
        Allow bracket notation for more Pythonic usage.
        
        Example:
            >>> count = cms["page1"]
        """
        return self.estimate(item)
    
    def merge(self, other):
        """
        Merge another Count-Min Sketch into this one.
        
        This is essential for distributed systems where each node maintains
        its own sketch and they need to be combined.
        
        The merge operation adds corresponding counters, which maintains
        the Count-Min Sketch properties and error guarantees.
        
        Args:
            other (CountMinSketch): Another sketch to merge
            
        Raises:
            ValueError: If sketches have different dimensions
            
        Time Complexity: O(d * w)
        
        Example use case:
            Three servers each track page views independently.
            Merge their sketches to get global view counts.
        """
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Cannot merge Count-Min Sketches with different dimensions")
        
        # Add all corresponding counters
        for i in range(self.depth):
            for j in range(self.width):
                self.table[i][j] += other.table[i][j]
        
        self.total_count += other.total_count
    
    def info(self):
        """
        Return comprehensive information about the sketch.
        
        Returns:
            dict: Configuration, statistics, and memory usage
        """
        # Estimate memory (assuming 8 bytes per integer counter)
        memory_bytes = self.width * self.depth * 8
        
        return {
            'width': self.width,
            'depth': self.depth,
            'total_counters': self.width * self.depth,
            'memory_bytes': memory_bytes,
            'memory_kb': memory_bytes / 1024,
            'memory_mb': memory_bytes / (1024 * 1024),
            'epsilon': self.epsilon,
            'delta': self.delta,
            'total_count': self.total_count,
            'max_error': self.epsilon * self.total_count,
            'confidence': 1 - self.delta
        }


class ConservativeCountMinSketch(CountMinSketch):
    """
    Conservative Count-Min Sketch - an improved variant.
    
    Improvement: When incrementing, only updates counters that would
    remain at the minimum value. This reduces overestimation for items
    that suffer from many hash collisions.
    
    The conservative update rule:
        1. Compute current estimates (minimums)
        2. Only increment counters that equal the current minimum
        3. This prevents "runaway" overestimation in heavily colliding counters
    
    Trade-off: Slightly more computation per update, but better accuracy.
    
    Reference:
        Estan & Varghese, "New directions in traffic measurement and 
        accounting" (2002)
    """
    
    def add(self, item, count=1):
        """
        Conservative update: only increment counters up to the minimum + count.
        
        Algorithm:
            1. Find current minimum count across all rows
            2. For each row, only update if counter equals minimum
            3. This prevents counters with many collisions from growing too large
        
        Args:
            item: Item to add
            count (int): Amount to increment
            
        Time Complexity: O(d) where d = depth
        """
        # Get current estimates from all rows
        counts = []
        positions = []
        for i in range(self.depth):
            col = self._hash(item, i)
            counts.append(self.table[i][col])
            positions.append((i, col))
        
        # Find current minimum
        min_count = min(counts)
        
        # Only update counters that equal the minimum
        # This is the "conservative" part - we don't let counters grow
        # too far above the minimum
        for (i, col), current_count in zip(positions, counts):
            if current_count == min_count:
                self.table[i][col] += count
        
        self.total_count += count


def demo():
    """
    Demonstrate Count-Min Sketch usage and accuracy.
    """
    print("=" * 70)
    print("Count-Min Sketch Demo")
    print("=" * 70)
    
    # Create sketch with 0.1% error tolerance, 99% confidence
    cms = CountMinSketch(epsilon=0.001, delta=0.01)
    
    print("\nConfiguration:")
    print(f"Error tolerance (epsilon): {cms.epsilon:.3f}")
    print(f"Confidence (1-delta): {1-cms.delta:.1%}")
    print(f"Dimensions: {cms.depth} rows × {cms.width} columns")
    print(f"Total counters: {cms.depth * cms.width:,}")
    info = cms.info()
    print(f"Memory: ~{info['memory_kb']:.2f} KB")
    
    # Simulate page view counting with realistic distribution
    print("\n" + "=" * 70)
    print("Simulating Page View Counting (Zipfian Distribution)")
    print("=" * 70)
    
    pages = [f"/page{i}" for i in range(100)]
    
    # Add counts with Zipfian distribution (realistic web traffic)
    # First pages get exponentially more views
    for i, page in enumerate(pages):
        views = int(10000 / (i + 1))
        for _ in range(views):
            cms.add(page)
    
    print(f"\nTotal page views tracked: {cms.total_count:,}")
    print(f"Max error bound: ±{cms.epsilon * cms.total_count:,.0f} views")
    
    # Check estimates for top pages
    print("\nTop 10 pages (actual vs estimated):")
    print(f"{'Page':<15} {'Actual':<12} {'Estimated':<12} {'Error'}")
    print("-" * 70)
    
    for i in range(10):
        page = pages[i]
        actual = int(10000 / (i + 1))
        estimated = cms.estimate(page)
        error = estimated - actual
        print(f"{page:<15} {actual:<12,} {estimated:<12,} {error:+,}")


if __name__ == "__main__":
    demo()
