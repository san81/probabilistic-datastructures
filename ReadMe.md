# Probabilistic Data Structures: Complete Guide

## Overview

This guide covers three fundamental probabilistic (approximate) algorithms that trade perfect accuracy for massive space savings:

1. **HyperLogLog** - Count unique items
2. **Bloom Filter** - Test set membership  
3. **Count-Min Sketch** - Count item frequencies

---

## 1. HyperLogLog

### Problem
Count unique elements (cardinality estimation) in a massive dataset without storing all elements.

### Key Insight
Rare events indicate large sample size. If you hash elements randomly and observe "I saw a run of 20 leading zeros", you probably processed ~2^20 unique elements.

### Algorithm
1. Hash each element (64-bit)
2. Use first `b` bits to select bucket (m = 2^b buckets)
3. Count leading zeros in remaining bits
4. Store max leading zeros per bucket
5. Estimate using harmonic mean: α × m² / Σ(2^(-max_i))

### Characteristics
- **Memory:** O(m) registers, typically 12-16 KB
- **Error:** ~1.04/√m (≈1% with m=16,384)
- **Updates:** O(1)
- **Merging:** O(m) - take max of each register

### When to Use
- Unique visitor counting (web analytics)
- Database: COUNT(DISTINCT) queries
- Network traffic: unique IP addresses
- Any cardinality estimation on streams

### Code Example
```python
hll = HyperLogLog(precision=14)  # 16K buckets, ~12KB memory
for user in users:
    hll.add(user)
print(f"Unique users: {hll.count()}")  # ±1% error
```

---

## 2. Bloom Filter

### Problem
Test if an element is in a set, using minimal memory, allowing small false positive rate.

### Key Insight
Use k hash functions to set k bits. To check membership, all k bits must be set.
- False positives: possible (collision)
- False negatives: IMPOSSIBLE

### Algorithm
1. Create bit array of size m (all 0s)
2. Use k hash functions
3. **Add:** Set bits at h₁(x), h₂(x), ..., hₖ(x) to 1
4. **Query:** Check if ALL k bits are 1

### Optimal Parameters
- m = -n·ln(p) / (ln(2))²  (size in bits)
- k = (m/n)·ln(2)  (number of hash functions)

Where:
- n = expected number of elements
- p = target false positive rate

### Characteristics
- **Memory:** ~10 bits per element for 1% FP rate
- **False Positive Rate:** Configurable (0.1% - 5%)
- **False Negative Rate:** 0% (never!)
- **Updates:** O(k)
- **Space Savings:** 90-95% vs storing actual elements

### When to Use
- Web crawler: avoid revisiting URLs
- Database: check cache before disk lookup
- Network: malicious URL detection
- Spell checkers: quickly reject invalid words

### Code Example
```python
bf = BloomFilter(expected_items=1000000, false_positive_rate=0.01)
bf.add("user123@example.com")

if email in bf:  # Fast check
    # Maybe in database (1% chance of false positive)
    check_database(email)
else:
    # Definitely NOT in database (100% certain)
    return "Not found"
```

---

## 3. Count-Min Sketch

### Problem
Track frequencies of items in a stream without storing exact counts for every item.

### Key Insight
Use multiple hash functions with counters. Due to collisions, counts are overestimated. Take the MINIMUM across all hash functions to get closest estimate.

### Algorithm
1. Create matrix: d rows × w columns (all 0s)
2. Use d hash functions (one per row)
3. **Update:** Increment counters at table[i][hash_i(item)] for all i
4. **Query:** Return min(table[0][hash_0(item)], ..., table[d-1][hash_{d-1}(item)])

### Optimal Parameters
- w = ⌈e/ε⌉ ≈ 2.718/ε  (width)
- d = ⌈ln(1/δ)⌉  (depth)

Where:
- ε = error tolerance (e.g., 0.001 = 0.1% error)
- δ = failure probability (e.g., 0.01 = 99% confidence)

### Characteristics
- **Memory:** O(w·d) counters
- **Guarantee:** Estimate ≥ True Count (never underestimates)
- **Error Bound:** estimate ≤ true + ε·N with probability 1-δ
- **Updates:** O(d)
- **Merging:** O(w·d) - add corresponding counters

### Variants
**Conservative Update:** Only increment counters that equal the minimum. Reduces overestimation.

### When to Use
- Heavy hitters: find most frequent items
- Rate limiting: count requests per IP
- Top-K queries: most viewed pages
- Anomaly detection: unusual frequency patterns
- Distributed monitoring: merge sketches from multiple servers

### Code Example
```python
cms = CountMinSketch(epsilon=0.001, delta=0.01)

# Track page views
for visit in stream:
    cms.add(visit.page)

# Query frequency (guaranteed >= actual)
print(f"Page views: {cms.estimate('/home')}")

# Find heavy hitters
for page in pages:
    if cms.estimate(page) > threshold:
        print(f"High traffic: {page}")
```

---

## Comparison Table

| Structure | Purpose | Memory | Error Type | False Negatives | Merging |
|-----------|---------|--------|------------|-----------------|---------|
| **HyperLogLog** | Count unique | ~12 KB | ±1% | N/A | ✓ Max |
| **Bloom Filter** | Membership | ~12 KB | 1% FP | Never | ✗ |
| **Count-Min** | Frequencies | ~100 KB | Overestimate | Never | ✓ Sum |

---

## Implementation Tips

### HyperLogLog
- Use precision 12-16 (trade-off: memory vs accuracy)
- SHA-1 or MurmurHash for hashing
- Apply small/large range corrections
- Perfect for distributed systems (just merge)

### Bloom Filter
- Calculate optimal m and k based on n and p
- Use double hashing: h_i(x) = h1(x) + i·h2(x)
- Monitor actual FP rate vs expected
- Consider Counting Bloom Filter for deletions

### Count-Min Sketch
- Start with ε=0.001, δ=0.01 (good defaults)
- Use Conservative Update for better accuracy
- Consider Count-Min-CU hybrid for hot items
- Perfect for distributed aggregation

---

## Mathematical Foundations

### HyperLogLog
```
E = α_m · m² · (Σ 2^(-M_j))^(-1)

where:
- m = number of buckets (2^precision)
- M_j = max leading zeros in bucket j
- α_m = bias correction constant
```

### Bloom Filter
```
False Positive Rate: p ≈ (1 - e^(-kn/m))^k

where:
- k = number of hash functions
- n = number of elements inserted
- m = size of bit array
```

### Count-Min Sketch
```
With probability ≥ 1-δ:
  count_estimate ≤ count_true + ε·N

where:
- ε = error tolerance
- δ = failure probability  
- N = total count of all items
```

---

## Real-World Applications

### Web Analytics
- HyperLogLog: Unique daily visitors
- Count-Min: Most viewed articles
- Bloom Filter: Unique clicks (before DB lookup)

### Networking
- HyperLogLog: Unique IP addresses
- Count-Min: DDoS detection (heavy hitters)
- Bloom Filter: Blacklist checking

### Databases
- HyperLogLog: COUNT(DISTINCT) approximation
- Count-Min: Top-K queries
- Bloom Filter: LSM-tree optimization

### Big Data
- HyperLogLog: Distinct elements in MapReduce
- Count-Min: Distributed frequency counting
- Bloom Filter: Distributed join optimization

---

## Space Complexity Analysis

For 1 million items:

**Exact Storage:**
- Hash Set: ~24 MB (24 bytes per pointer)
- Counter Dict: ~48 MB (key + value)

**Approximate Storage:**
- HyperLogLog: 12 KB (0.05% of exact!)
- Bloom Filter (1% FP): 1.2 MB (5% of exact)
- Count-Min (0.1% error): 100 KB (0.2% of exact)

---

## When NOT to Use

### Don't use probabilistic structures when:
1. You need exact counts (compliance, billing)
2. Dataset fits comfortably in memory
3. False positives/overestimation unacceptable
4. Need to retrieve actual elements (only test membership)
5. Need deletions (except Counting Bloom Filter)

---

## Further Reading

### Papers
- HyperLogLog: Flajolet et al., "HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm" (2007)
- Bloom Filter: Bloom, "Space/time trade-offs in hash coding with allowable errors" (1970)
- Count-Min Sketch: Cormode & Muthukrishnan, "An improved data stream summary: the count-min sketch" (2005)

### Libraries
- **Python:** `datasketch`, `pybloom-live`, `redis` (built-in support)
- **Java:** `stream-lib`, `Guava` (BloomFilter)
- **Go:** `boom`, `hyperloglog`
- **Redis:** Native HyperLogLog, Bloom Filter (RedisBloom)

---

## Quiz Questions

1. Why does HyperLogLog use multiple buckets instead of just one?
   - Reduces variance, improves accuracy through averaging

2. Can Bloom Filters have false negatives?
   - No! If it says "not present", it's 100% certain

3. Why does Count-Min Sketch return the MINIMUM?
   - Collisions only increase counts, so minimum is closest to truth

4. Which structure can be used for deletions?
   - Counting Bloom Filter (uses counters instead of bits)

5. Which structure guarantees never underestimating?
   - Count-Min Sketch (always overestimates due to collisions)
