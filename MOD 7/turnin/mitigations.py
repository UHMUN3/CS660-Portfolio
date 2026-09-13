"""
mitigations.py -- Measures the mitigation options instead of just naming them.

CS 660 Module Seven Activity, rubric criterion 4.

The activity asks for recommended mitigations when a requirement is not met,
and suggests PyPy, NumPy, Cython, or a different language. Rather than assert
which of those would help, this module benchmarks the ones installed on the
machine, using the same harness from benchmark.py -- which is the real test of
whether that harness is reusable.

Options measured
----------------
  pure Python quick_sort   the baseline being mitigated
  list.sort                CPython's Timsort, written in C -- zero-effort option
  numpy.sort               introsort over a packed C int64 buffer
  C quicksort (ctypes)     the SAME algorithm as sorts.quick_sort, compiled;
                           stands in for Cython or a C extension
  libc qsort (ctypes)      the C standard library's sort, for reference

Sort-only vs round trip
-----------------------
Every native option is measured twice, and the gap between the two is the
actual engineering decision:

  "sort only"   the data already lives in a native buffer (ndarray or C array).
                This is the number you get if the whole pipeline is rewritten
                to keep data out of Python objects.

  "round trip"  the data arrives as a Python list and must be converted in and
                converted back. This is the number you get if you swap in a
                fast sort and change nothing else.

A mitigation that looks like a 100x win sort-only can shrink to far less once
marshalling is counted, and that distinction is what separates a real
recommendation from a benchmark screenshot.

A measurement caveat, stated because it affects how the memory column reads:
tracemalloc only sees allocations made through CPython's own allocator. NumPy
and the ctypes buffers call malloc directly, so their data buffers are
INVISIBLE to tracemalloc and show as ~0 MB. For those rows the true buffer size
is reported separately from ndarray.nbytes / the ctypes array size, and process
RSS is used as a cross-check.

Usage:
    python3 mitigations.py
    python3 mitigations.py --n 100000 --iterations 5
    taskpolicy -b python3 mitigations.py --tier e-core
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import os
import platform
import random
import resource
import sys
import time

from benchmark import benchmark, print_table, write_csv, write_json
from sorts import quick_sort

_BYTES_PER_MB = 1024 * 1024


# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:
    import numpy as np
except ImportError:
    np = None


def load_c_library():
    """Load libcsort, building it first if needed. Returns None if unavailable."""
    here = os.path.dirname(os.path.abspath(__file__))
    suffix = ".dylib" if platform.system() == "Darwin" else ".so"
    lib_path = os.path.join(here, "libcsort" + suffix)

    if not os.path.exists(lib_path):
        source = os.path.join(here, "csort.c")
        if not os.path.exists(source):
            return None
        if os.system(f'cc -O2 -shared -fPIC -o "{lib_path}" "{source}"') != 0:
            return None

    lib = ctypes.CDLL(lib_path)
    for name in ("c_quicksort_i64", "c_libc_qsort_i64"):
        fn = getattr(lib, name)
        fn.argtypes = [ctypes.POINTER(ctypes.c_longlong), ctypes.c_long]
        fn.restype = None
    return lib


# ---------------------------------------------------------------------------
# Memory helpers for native buffers that tracemalloc cannot see
# ---------------------------------------------------------------------------

def rss_mb() -> float:
    """Process resident set size in MB. ru_maxrss is bytes on macOS, KB on Linux."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / _BYTES_PER_MB if platform.system() == "Darwin" else raw / 1024


def python_list_mb(n: int, distinct: bool = True) -> float:
    """True cost of a Python list of n integers: pointer array + int objects."""
    pointers = 8 * n
    boxes = sys.getsizeof(10**9) * n if distinct else 0
    return (pointers + boxes) / _BYTES_PER_MB


def native_buffer_mb(n: int) -> float:
    """Cost of the same n integers as a packed 64-bit C buffer."""
    return (8 * n) / _BYTES_PER_MB


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100_000)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--tier", default="default")
    parser.add_argument("--out", default="results")
    args = parser.parse_args(argv)

    n, iters = args.n, args.iterations
    rng = random.Random(660)
    data = [rng.randint(0, 10**9) for _ in range(n)]
    expected = sorted(data)

    print("=" * 78)
    print(f"MITIGATION MEASUREMENTS  (n = {n:,}, random integers, tier={args.tier})")
    print("=" * 78)

    results = []

    # --- Baseline: what we are trying to fix -------------------------------
    results.append(benchmark(quick_sort, data, iters,
                             label="quick_sort (pure Python)",
                             dataset="baseline",
                             input_mb=python_list_mb(n)))

    # --- Mitigation 0: use the C sort already in the standard library ------
    results.append(benchmark(list.sort, data, iters,
                             label="list.sort [C Timsort]",
                             dataset="stdlib",
                             input_mb=python_list_mb(n)))

    # --- Mitigation 1: NumPy ------------------------------------------------
    if np is not None:
        arr = np.array(data, dtype=np.int64)
        ok = lambda produced, original: list(produced) == expected

        results.append(benchmark(
            np.ndarray.sort, arr, iters,
            label="numpy sort [sort only]", dataset="numpy",
            input_mb=native_buffer_mb(n),
            copy_function=np.copy, validator=ok))

        def numpy_round_trip(values):
            """list -> ndarray -> sort -> list, the drop-in replacement path."""
            a = np.array(values, dtype=np.int64)
            a.sort()
            return a.tolist()

        results.append(benchmark(
            numpy_round_trip, data, iters,
            label="numpy sort [round trip]", dataset="numpy",
            input_mb=python_list_mb(n)))
    else:
        print("\n  numpy not installed -- skipping NumPy rows")

    # --- Mitigation 2: compiled C via ctypes (stands in for Cython) --------
    lib = load_c_library()
    if lib is not None:
        BufferType = ctypes.c_longlong * n
        c_buffer = BufferType(*data)

        def copy_buffer(buf):
            new = BufferType()
            ctypes.memmove(new, buf, ctypes.sizeof(buf))
            return new

        def c_sort_only(buf):
            lib.c_quicksort_i64(buf, n)
            return buf

        def c_libc_only(buf):
            lib.c_libc_qsort_i64(buf, n)
            return buf

        ok_buf = lambda produced, original: list(produced) == expected

        results.append(benchmark(
            c_sort_only, c_buffer, iters,
            label="C quicksort [sort only]", dataset="ctypes",
            input_mb=native_buffer_mb(n),
            copy_function=copy_buffer, validator=ok_buf))

        results.append(benchmark(
            c_libc_only, c_buffer, iters,
            label="libc qsort [sort only]", dataset="ctypes",
            input_mb=native_buffer_mb(n),
            copy_function=copy_buffer, validator=ok_buf))

        def c_round_trip(values):
            """list -> C array -> sort -> list, the drop-in replacement path."""
            buf = BufferType(*values)
            lib.c_quicksort_i64(buf, len(values))
            return list(buf)

        results.append(benchmark(
            c_round_trip, data, iters,
            label="C quicksort [round trip]", dataset="ctypes",
            input_mb=python_list_mb(n)))
    else:
        print("\n  C library unavailable -- skipping ctypes rows")

    print_table(results, title="MITIGATION OPTIONS", budget_ms=400.0)

    # --- Speedups relative to the pure-Python baseline ---------------------
    base = results[0].avg_time_ms
    print("\n" + "=" * 78)
    print("SPEEDUP vs pure-Python quick_sort")
    print("=" * 78)
    for r in results:
        verdict = "within budget" if r.avg_time_ms < 400.0 else "OVER BUDGET"
        print(f"  {r.function:28s} {r.avg_time_ms:9.2f} ms"
              f"   {base / r.avg_time_ms:7.1f}x   {verdict}")

    # --- The conversion cost, isolated -------------------------------------
    print("\n" + "=" * 78)
    print("WHERE THE ROUND-TRIP TIME GOES")
    print("=" * 78)
    if np is not None:
        gc.collect()
        t = time.perf_counter(); a = np.array(data, dtype=np.int64)
        to_np = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); a.sort()
        np_sort = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); a.tolist()
        from_np = (time.perf_counter() - t) * 1000
        print(f"  numpy: list->ndarray {to_np:7.2f} ms"
              f" | sort {np_sort:6.2f} ms"
              f" | ndarray->list {from_np:7.2f} ms")
        print(f"         conversion is {(to_np + from_np) / (to_np + np_sort + from_np) * 100:.0f}%"
              f" of the round trip")

    # --- Memory comparison, including what tracemalloc cannot see ----------
    print("\n" + "=" * 78)
    print("MEMORY: PYTHON LIST vs PACKED NATIVE BUFFER")
    print("=" * 78)
    py_mb, native_mb = python_list_mb(n), native_buffer_mb(n)
    print(f"  Python list of {n:,} distinct ints"
          f"   {py_mb:7.2f} MB   (8-byte pointer + {sys.getsizeof(10**9)}-byte int object each)")
    print(f"  int64 buffer of {n:,} values"
          f"    {native_mb:7.2f} MB   (8 bytes each, no object header)")
    print(f"  reduction                          {py_mb / native_mb:7.1f}x")
    print(f"\n  process RSS at end of run          {rss_mb():7.2f} MB")
    print("  (tracemalloc shows ~0 MB for the numpy and ctypes rows because those")
    print("   buffers come from malloc, not CPython's allocator -- see module docstring)")

    os.makedirs(args.out, exist_ok=True)
    write_csv(results, os.path.join(args.out, f"mitigations_{args.tier}.csv"))
    write_json(results, os.path.join(args.out, f"mitigations_{args.tier}.json"))
    print(f"\nSaved to {args.out}/mitigations_{args.tier}.{{csv,json}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
