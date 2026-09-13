"""
run_benchmarks.py -- Driver that judges Python against the stakeholders' targets.

CS 660 Module Seven Activity.

Stakeholder requirements under test:
    1. Sort 100,000 integers in under 400 ms on standard hardware
    2. Keep peak memory under 50 MB during the sort
    3. Provide a reusable in-house benchmarking harness  (-> benchmark.py)

Usage
-----
    python3 run_benchmarks.py                    # full run, P-cores
    python3 run_benchmarks.py --iterations 10    # more samples
    python3 run_benchmarks.py --quick            # skip the scaling study
    python3 run_benchmarks.py --tier e-core      # tag the run's output

    taskpolicy -b python3 run_benchmarks.py --tier e-core
        Runs pinned to the efficiency cores on Apple silicon. This is the
        "slower standard hardware" comparison -- see the README. It is the
        difference between a result that is true of this laptop and a result
        that is true of the requirement.
"""

from __future__ import annotations

import argparse
import os
import random
import sys

from benchmark import (
    benchmark_suite,
    environment_info,
    measure_input_footprint,
    print_table,
    write_csv,
    write_json,
)
from sorts import quick_sort, merge_sort, heap_sort

# --- The stakeholders' hard requirements ----------------------------------
TARGET_N = 100_000
BUDGET_MS = 400.0
BUDGET_MB = 50.0

SEED = 660          # fixed so every run sorts the identical data


# ---------------------------------------------------------------------------
# Input distributions
# ---------------------------------------------------------------------------

def make_random(n, seed=SEED):
    rng = random.Random(seed)
    return [rng.randint(0, 10**9) for _ in range(n)]


def make_sorted(n, seed=SEED):
    return sorted(make_random(n, seed))


def make_reversed(n, seed=SEED):
    return sorted(make_random(n, seed), reverse=True)


def make_nearly_sorted(n, seed=SEED):
    """Sorted, then 1% of elements swapped -- a common real-world shape."""
    data = sorted(make_random(n, seed))
    rng = random.Random(seed + 1)
    for _ in range(max(1, n // 100)):
        i, j = rng.randrange(n), rng.randrange(n)
        data[i], data[j] = data[j], data[i]
    return data


def make_few_unique(n, seed=SEED):
    """Only 100 distinct values -- stresses partitioning and shows int caching."""
    rng = random.Random(seed)
    return [rng.randint(0, 99) for _ in range(n)]


DISTRIBUTIONS = {
    "random": make_random,
    "sorted": make_sorted,
    "reversed": make_reversed,
    "nearly_sorted": make_nearly_sorted,
    "few_unique": make_few_unique,
}

# list.sort is CPython's Timsort, written in C. It is not one of the three
# algorithms the activity asks for; it is the control that separates
# "this algorithm is slow" from "the interpreter is slow".
FUNCTIONS = [
    ("quick_sort", quick_sort),
    ("merge_sort", merge_sort),
    ("heap_sort", heap_sort),
    ("list.sort [C]", list.sort),
]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_environment():
    info = environment_info()
    print("=" * 78)
    print("BENCHMARK ENVIRONMENT")
    print("=" * 78)
    for key, value in info.items():
        print(f"  {key:22s} {value}")
    print(f"  {'cpu_count':22s} {os.cpu_count()}")
    print()
    print(f"  Requirement 1: sort {TARGET_N:,} integers in < {BUDGET_MS:.0f} ms")
    print(f"  Requirement 2: peak memory < {BUDGET_MB:.0f} MB")
    print(f"  Requirement 3: reusable benchmarking harness -> benchmark.py")


def print_requirements_verdict(results):
    """Judge each requirement against the random-input results at the target n."""
    target = [r for r in results
              if r.n == TARGET_N and r.dataset == "random"
              and not r.function.startswith("list.sort")]
    if not target:
        return

    print("\n" + "=" * 78)
    print(f"REQUIREMENTS VERDICT  (n = {TARGET_N:,}, random input)")
    print("=" * 78)

    fastest = min(target, key=lambda r: r.avg_time_ms)
    leanest = min(target, key=lambda r: r.peak_total_mb)

    time_ok = fastest.avg_time_ms < BUDGET_MS
    mem_ok = leanest.peak_total_mb < BUDGET_MB

    print(f"\n  R1  < {BUDGET_MS:.0f} ms")
    for r in sorted(target, key=lambda r: r.avg_time_ms):
        mark = "PASS" if r.avg_time_ms < BUDGET_MS else "FAIL"
        margin = BUDGET_MS / r.avg_time_ms
        print(f"        {mark}  {r.function:14s} {r.avg_time_ms:8.1f} ms"
              f"   ({margin:.2f}x budget)")
    print(f"      -> {'MET' if time_ok else 'NOT MET'}"
          f" (best: {fastest.function} at {fastest.avg_time_ms:.1f} ms)")

    print(f"\n  R2  < {BUDGET_MB:.0f} MB")
    for r in sorted(target, key=lambda r: r.peak_total_mb):
        mark = "PASS" if r.peak_total_mb < BUDGET_MB else "FAIL"
        margin = BUDGET_MB / r.peak_total_mb if r.peak_total_mb else float("inf")
        print(f"        {mark}  {r.function:14s} {r.peak_total_mb:8.2f} MB"
              f"   (input {r.input_mb:.2f} + sort {r.peak_alloc_mb:.2f},"
              f" {margin:.1f}x headroom)")
    print(f"      -> {'MET' if mem_ok else 'NOT MET'}"
          f" (best: {leanest.function} at {leanest.peak_total_mb:.2f} MB)")

    print(f"\n  R3  reusable harness -> benchmark.py: MET")

    baseline = [r for r in results
                if r.n == TARGET_N and r.dataset == "random"
                and r.function.startswith("list.sort")]
    if baseline:
        b = baseline[0]
        print(f"\n  Reference: list.sort (C Timsort) {b.avg_time_ms:.1f} ms"
              f" -- {fastest.avg_time_ms / b.avg_time_ms:.1f}x faster than the"
              f" best pure-Python sort.")
        print("  That ratio is the interpreter tax, not an algorithmic difference.")


def print_scaling(results):
    print("\n" + "=" * 78)
    print("SCALING  (random input, avg ms)")
    print("=" * 78)

    sizes = sorted({r.n for r in results})
    names = []
    for r in results:
        if r.function not in names:
            names.append(r.function)

    header = f"{'n':>10s}  " + "  ".join(f"{nm:>14s}" for nm in names)
    print(header)
    print("-" * len(header))
    for n in sizes:
        row = f"{n:>10,}  "
        cells = []
        for nm in names:
            match = [r for r in results if r.n == n and r.function == nm]
            cells.append(f"{match[0].avg_time_ms:>14,.2f}" if match else f"{'-':>14s}")
        print(row + "  ".join(cells))

    # Doubling ratio: n log n predicts ~2.1x per doubling, n^2 predicts ~4x.
    print("\n  Time ratio per doubling of n (n log n predicts ~2.1x):")
    for nm in names:
        pts = sorted(((r.n, r.avg_time_ms) for r in results if r.function == nm))
        ratios = [f"{b[1]/a[1]:.2f}x" for a, b in zip(pts, pts[1:]) if a[1] > 0]
        print(f"    {nm:16s} {'  '.join(ratios)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5,
                        help="timed runs to average per measurement (default 5)")
    parser.add_argument("--quick", action="store_true",
                        help="skip the scaling study")
    parser.add_argument("--tier", default="default",
                        help="label for this run, e.g. p-core / e-core")
    parser.add_argument("--out", default="results",
                        help="directory for CSV and JSON output")
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    print_environment()
    print(f"\n  run tier: {args.tier}   iterations: {args.iterations}")

    # --- Study 1: every algorithm against every distribution, at target n ---
    datasets = {
        name: (lambda f=factory: f(TARGET_N))
        for name, factory in DISTRIBUTIONS.items()
    }
    print(f"\nRunning {len(FUNCTIONS)} functions x {len(datasets)} distributions "
          f"at n={TARGET_N:,} ...")
    main_results = benchmark_suite(FUNCTIONS, datasets, args.iterations)

    print_table(main_results,
                title=f"ALL ALGORITHMS x ALL DISTRIBUTIONS  (n = {TARGET_N:,})",
                budget_ms=BUDGET_MS, budget_mb=BUDGET_MB)

    print_requirements_verdict(main_results)

    # --- Study 2: how cost grows with n ------------------------------------
    scaling_results = []
    if not args.quick:
        sizes = [10_000, 25_000, 50_000, 100_000, 200_000]
        print(f"\nRunning scaling study at n = {', '.join(f'{s:,}' for s in sizes)} ...")
        scaling_datasets = {
            str(n): (lambda n=n: make_random(n)) for n in sizes
        }
        scaling_results = benchmark_suite(
            FUNCTIONS, scaling_datasets,
            max(3, args.iterations // 2),
            measure_memory=False, validate=False,
        )
        for r in scaling_results:
            r.dataset = "random"
            r.notes = "scaling study"
        print_scaling(scaling_results)

    # --- Persist -----------------------------------------------------------
    all_results = main_results + scaling_results
    csv_path = os.path.join(args.out, f"results_{args.tier}.csv")
    json_path = os.path.join(args.out, f"results_{args.tier}.json")
    write_csv(all_results, csv_path)
    write_json(all_results, json_path)
    print(f"\nSaved {len(all_results)} results to:")
    print(f"  {csv_path}")
    print(f"  {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
