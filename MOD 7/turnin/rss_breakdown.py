"""
rss_breakdown.py -- What actually occupies the 50 MB memory budget.

CS 660 Module Seven Activity.

tracemalloc answers "how much did the sort allocate". A stakeholder who writes
"keep peak memory below fifty megabytes" is usually asking a different
question: "how big does the process get". Those two numbers differ by the
entire cost of the interpreter, and on this requirement the difference decides
whether Python passes.

This script reports resident set size (RSS) as the process grows step by step,
so the 50 MB budget can be read against the real footprint rather than against
the sort's incremental allocation alone.
"""

import gc
import platform
import resource
import subprocess
import sys

MB = 1024 * 1024


def rss_mb():
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / MB if platform.system() == "Darwin" else raw / 1024


def report(label, value, budget=50.0):
    bar = "OVER BUDGET" if value > budget else ""
    print(f"  {label:44s} {value:8.2f} MB  {bar}")


print("=" * 78)
print("PROCESS MEMORY vs THE 50 MB BUDGET")
print("=" * 78)

# A truly empty interpreter, measured from outside this process.
bare = subprocess.run(
    [sys.executable, "-c",
     "import resource,platform;"
     "r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;"
     "print(r/1048576 if platform.system()=='Darwin' else r/1024)"],
    capture_output=True, text=True)
print()
report("bare CPython interpreter, nothing imported", float(bare.stdout.strip()))

report("this script, before allocating data", rss_mb())

import random
rng = random.Random(660)
data = [rng.randint(0, 10**9) for _ in range(100_000)]
report("+ list of 100,000 distinct ints", rss_mb())

from sorts import merge_sort
merged = merge_sort(data)
report("+ merge_sort output (allocates a new list)", rss_mb())
del merged
gc.collect()

try:
    import numpy as np
    report("+ import numpy", rss_mb())
    arr = np.array(data, dtype=np.int64)
    report("+ ndarray of the same 100,000 ints", rss_mb())
except ImportError:
    print("  (numpy not installed)")

print()
print("=" * 78)
print("READING THE REQUIREMENT")
print("=" * 78)
print("""
  Interpreted as "bytes the sort allocates" (tracemalloc):
      quick_sort / heap_sort  ~0.00 MB   merge_sort  ~1.65 MB   -> PASSES easily

  Interpreted as "bytes the sort allocates, plus the data":
      3.8 - 5.5 MB                                              -> PASSES, ~9-13x headroom

  Interpreted as "resident size of the process":
      dominated by the interpreter itself, not by the sort      -> see above

  The 100,000 integers cost under 4 MB. Whether Python meets a 50 MB budget is
  therefore decided almost entirely by fixed interpreter and library overhead,
  which no choice of sorting algorithm can influence.
""")
