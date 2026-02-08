# Probabilistic Data Structures

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

High-performance implementations of three fundamental probabilistic data structures that trade perfect accuracy for massive space savings:

1. **HyperLogLog** - Count unique elements with ~1% error using only 12KB
2. **Bloom Filter** - Test set membership with configurable false positive rates
3. **Count-Min Sketch** - Estimate item frequencies with guaranteed bounds

## 🎯 Why Probabilistic Data Structures?

Traditional exact data structures can become prohibitively expensive when dealing with massive datasets:

- **Exact Set**: 1M emails × 30 bytes = **30 MB**
- **Bloom Filter**: 1M emails × 10 bits = **1.2 MB** (96% savings!)

| Data Structure | Purpose | Memory | Guarantee |
|----------------|---------|--------|-----------|
| HyperLogLog | Count unique | ~12 KB | ±1% error |
| Bloom Filter | Set membership | ~1.2 MB | No false negatives |
| Count-Min Sketch | Frequencies | ~106 KB | Never underestimates |

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/san81/probabilistic-datastructures.git
cd probabilistic-datastructures

# No dependencies required - uses only Python standard library!
```

## 🚀 Quick Start

### HyperLogLog - Count Unique Elements

```python
from hyperloglog import HyperLogLog

# Create HLL with precision 14 (~16K buckets, ~16KB memory)
hll = HyperLogLog(precision=14)

# Add elements
for user_id in user_stream:
    hll.add(user_id)

# Get cardinality estimate
unique_users = hll.count()
print(f"Unique visitors: {unique_users:,.0f}")  # ±1% error

# Merge multiple HLLs (e.g., from distributed systems)
hll1.merge(hll2)
```

**Use Cases:**
- Unique visitor counting (web analytics)
- Database COUNT(DISTINCT) approximation
- Network traffic: unique IP addresses
- Distinct elements in MapReduce

### Bloom Filter - Fast Membership Testing

```python
from bloomfilter import BloomFilter

# Create filter for 1M items with 1% false positive rate
bf = BloomFilter(expected_items=1000000, false_positive_rate=0.01)

# Add elements
bf.add("user@example.com")
bf.add("admin@example.com")

# Test membership
if "user@example.com" in bf:
    print("Probably in database")  # Might be false positive
else:
    print("Definitely NOT in database")  # 100% certain!

# Check statistics
print(f"Utilization: {bf.utilization():.2f}%")
print(f"Actual FP rate: {bf.actual_false_positive_rate():.4%}")
```

**Use Cases:**
- Cache filtering (check before expensive DB lookup)
- URL deduplication in web crawlers
- Malicious URL detection
- Spell checkers

### Count-Min Sketch - Frequency Estimation

```python
from countminsketch import CountMinSketch

# Create sketch with 0.1% error, 99% confidence
cms = CountMinSketch(epsilon=0.001, delta=0.01)

# Count events
for page_view in stream:
    cms.add(page_view.page)

# Estimate frequency (always >= true count)
views = cms.estimate("/home")
print(f"Page views: ~{views:,}")

# Find heavy hitters
for page in all_pages:
    if cms.estimate(page) > threshold:
        print(f"High traffic: {page}")

# Merge sketches from distributed systems
cms1.merge(cms2)
cms1.merge(cms3)
```

**Use Cases:**
- Top-K queries (most viewed pages)
- DDoS detection (heavy hitters)
- Rate limiting
- Distributed monitoring

## 📊 Performance & Accuracy

### HyperLogLog Accuracy Test

```
Actual: 100          Estimated: 100       Error: 0.31%
Actual: 1,000        Estimated: 1,000     Error: 0.01%
Actual: 10,000       Estimated: 10,006    Error: 0.06%
Actual: 100,000      Estimated: 100,650   Error: 0.65%
```

### Bloom Filter Space Savings

```
Storing 10,000 emails:
  Python set:     ~184.6 KB
  Bloom filter:   ~11.7 KB
  Space savings:  93.7%
```

### Count-Min Sketch Guarantees

With probability ≥ 99% (δ=0.01):
```
estimate ≤ true_count + ε × total_count
```

For ε=0.001 and total=1M:
```
Max error: ±1,000 (0.1% of total)
```

## 🧪 Running Tests

Comprehensive test suites are included for all data structures:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python tests/test_hyperloglog.py
python tests/test_bloomfilter.py
python tests/test_countminsketch.py

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

Each implementation includes:
- ✅ Basic functionality tests
- ✅ Accuracy and error bound verification
- ✅ Edge case handling
- ✅ Performance benchmarks
- ✅ Real-world scenario simulations

## 📚 API Documentation

### HyperLogLog

```python
class HyperLogLog:
    def __init__(self, precision=14):
        """
        Args:
            precision: 4-16 (higher = more accurate, more memory)
        """
    
    def add(self, value):
        """Add element. O(1)"""
    
    def count(self) -> float:
        """Estimate cardinality. O(m)"""
    
    def merge(self, other):
        """Merge two HLLs. O(m)"""
```

### Bloom Filter

```python
class BloomFilter:
    def __init__(self, expected_items=10000, false_positive_rate=0.01):
        """
        Args:
            expected_items: Expected number of elements
            false_positive_rate: Target FP rate (0-1)
        """
    
    def add(self, item):
        """Add element. O(k)"""
    
    def contains(self, item) -> bool:
        """Check membership. O(k)"""
    
    def actual_false_positive_rate(self) -> float:
        """Calculate current FP rate"""
```

### Count-Min Sketch

```python
class CountMinSketch:
    def __init__(self, epsilon=0.001, delta=0.01):
        """
        Args:
            epsilon: Error tolerance (0-1)
            delta: Failure probability (0-1)
        """
    
    def add(self, item, count=1):
        """Increment count. O(d)"""
    
    def estimate(self, item) -> int:
        """Estimate frequency. O(d). Always >= true count"""
    
    def merge(self, other):
        """Merge two sketches. O(d × w)"""
```

## 🔬 Algorithm Details

### HyperLogLog

**Intuition:** Rare events indicate large sample size. If you hash elements and observe "20 leading zeros", you probably processed ~2²⁰ unique elements.

**Algorithm:**
1. Hash each element (64-bit)
2. Use first `p` bits for bucket selection (m = 2^p buckets)
3. Count leading zeros in remaining bits
4. Keep maximum per bucket
5. Estimate using harmonic mean

**Formula:**
```
E = α_m × m² / Σ(2^(-M_j))
```

### Bloom Filter

**Intuition:** Use k hash functions to set k bits. To check: all k bits must be set. If any is 0 → definitely not in set.

**Algorithm:**
1. Bit array of size m
2. k hash functions
3. Add: set k bits to 1
4. Query: check if all k bits are 1

**Optimal Parameters:**
```
m = -n × ln(p) / (ln(2))²  (bits)
k = (m/n) × ln(2)          (hashes)
```

### Count-Min Sketch

**Intuition:** Use multiple hash tables with counters. Hash collisions only increase counts. Take minimum across rows.

**Algorithm:**
1. 2D array: d rows × w columns
2. d hash functions (one per row)
3. Add: increment d counters
4. Query: return minimum of d counters

**Optimal Parameters:**
```
w = ⌈e/ε⌉  (width)
d = ⌈ln(1/δ)⌉  (depth)
```

## 🎓 When to Use Each Structure

### Use HyperLogLog when:
- ✅ Need to count unique elements
- ✅ Dataset too large to store all elements
- ✅ ~1% error is acceptable
- ✅ Need to merge counts from distributed systems

### Use Bloom Filter when:
- ✅ Need fast set membership tests
- ✅ False positives are acceptable
- ✅ False negatives are NOT acceptable
- ✅ Want 90-95% space savings

### Use Count-Min Sketch when:
- ✅ Need to track item frequencies
- ✅ Overestimation is acceptable (underestimation is not)
- ✅ Need to merge from distributed systems
- ✅ Finding top-K items

## ⚠️ When NOT to Use

Don't use probabilistic structures when:
- ❌ Need exact counts (billing, compliance)
- ❌ Dataset fits comfortably in memory
- ❌ Any error is unacceptable
- ❌ Need to retrieve actual elements

## 📖 References

### Papers
- **HyperLogLog:** Flajolet et al., "HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm" (2007)
- **Bloom Filter:** Bloom, "Space/time trade-offs in hash coding with allowable errors" (1970)
- **Count-Min Sketch:** Cormode & Muthukrishnan, "An improved data stream summary: the count-min sketch" (2005)

### Further Reading
- [HyperLogLog in Practice](https://research.google/pubs/pub40671/)
- [Bloom Filters by Example](https://llimllib.github.io/bloomfilter-tutorial/)
- [Count-Min Sketch Applications](https://dl.acm.org/doi/10.1145/1142473.1142503)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`python -m pytest tests/ -v`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Santhosh Gandhe**
- GitHub: [@san81](https://github.com/san81)

## 🙏 Acknowledgments

- Implementations based on original papers
- Inspired by production systems at Google, Twitter, and Redis
- Thanks to the computer science community for these elegant algorithms

## 📬 Questions?

- Open an issue on GitHub
- Check the [examples](examples/) directory
- Review the comprehensive test suites

---

**⭐ If you find this useful, please star the repository!**
