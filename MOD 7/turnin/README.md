# CS 660 — Module Seven Activity

Benchmarking three sorting algorithms in Python and judging the language against
three stakeholder requirements.

| # | Requirement | Verdict |
|---|---|---|
| R1 | Sort 100,000 integers in **< 400 ms** | **Conditional** — 84 ms on performance cores, 405 ms on efficiency cores |
| R2 | Peak memory **< 50 MB** | **Met** — 3.8–5.5 MB of data, 21.6 MB process total |
| R3 | Reusable benchmarking harness | **Met** — `benchmark.py` |

## Files

| File | Purpose |
|---|---|
| `sorts.py` | Quick sort, merge sort, heap sort — pure Python, no built-in sorting |
| `benchmark.py` | The reusable harness (rubric criterion 2) |
| `run_benchmarks.py` | Driver — judges all three algorithms against R1–R3 |
| `mitigations.py` | Measures NumPy, ctypes/C, and `list.sort` as mitigations |
| `rss_breakdown.py` | Process memory against the 50 MB budget |
| `csort.c` | C quicksort, algorithmically identical to `sorts.quick_sort` |
| `results/` | Raw CSV + JSON for both hardware tiers |
| `CS660_Module7_Activity_Report.docx` | The written report |

## Running

```bash
python3 run_benchmarks.py --tier p-core     # full suite
python3 mitigations.py --tier p-core        # mitigation options
python3 rss_breakdown.py                    # memory vs the 50 MB budget
```

Useful flags: `--iterations N`, `--quick` (skip the scaling study), `--out DIR`.

### The slow-hardware comparison

An M4 Max is not "standard hardware," so measuring only on it answers the wrong
question. On Apple silicon, `taskpolicy -b` runs a process at background
quality-of-service, which the scheduler confines to the efficiency cores. That
gives two hardware tiers from one machine with everything else held constant:

```bash
taskpolicy -b python3 run_benchmarks.py --tier e-core
```

This is what turns R1 from a pass into a conditional pass. On efficiency cores
quick sort averages 405 ms and exceeds the 400 ms budget on 6 of 12 runs.

## Using the harness on your own code

`benchmark.py` knows nothing about sorting — it takes any callable and any sized
sequence.

```python
from benchmark import benchmark, print_table, write_csv

result = benchmark(my_function, my_data, iterations=10)
print_table([result], budget_ms=400, budget_mb=50)
write_csv([result], "results.csv")
```

For inputs that are not Python lists, pass `copy_function` and `validator`:

```python
import numpy as np
benchmark(np.ndarray.sort, arr, 5,
          copy_function=np.copy,
          validator=lambda produced, original: list(produced) == sorted(original.tolist()))
```

## Notes on the measurements

- **Timing and memory run in separate passes.** `tracemalloc` inflates runtime
  several-fold, so timing anything while it runs measures the profiler.
- **Every iteration gets a fresh copy of the input,** made outside the timed
  region. `quick_sort` and `heap_sort` mutate their argument; without this the
  second iteration would sort already-sorted data.
- **`tracemalloc` cannot see NumPy or ctypes buffers.** Those come from `malloc`
  rather than CPython's allocator and report as 0.00 MB. `mitigations.py` reports
  buffer size and process RSS for those rows instead.
- **Seed is fixed at 660,** so every run sorts identical data.

## Rebuilding the C library

`mitigations.py` builds it automatically if missing. Manually:

```bash
cc -O2 -shared -fPIC -o libcsort.dylib csort.c   # macOS
cc -O2 -shared -fPIC -o libcsort.so    csort.c   # Linux
```

Requires Python 3.10+. NumPy is optional — those rows are skipped if absent.
