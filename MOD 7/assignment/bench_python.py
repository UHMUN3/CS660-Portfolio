"""Python side of the Python vs Go benchmark.

CS 660 Module Seven Assignment.

Reads the SAME shared_input.txt the Go program reads and runs the same three
algorithms through the harness built for the Module Seven Activity. Reusing
that harness rather than writing a new one keeps the Python methodology
identical to what the Activity reported, and is a second demonstration that the
harness is genuinely reusable.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark import benchmark, print_table, environment_info   # noqa: E402
from sorts import quick_sort, merge_sort, heap_sort              # noqa: E402

INPUT = "shared_input.txt"
OUT = "results/python_results.json"
ITERATIONS = 5


def load(path):
    with open(path) as fh:
        return [int(line) for line in fh if line.strip()]


def main():
    data = load(INPUT)
    info = environment_info()

    print("=" * 62)
    print("PYTHON BENCHMARK")
    print("=" * 62)
    print(f"  python        {info['implementation']} {info['python_version']}")
    print(f"  platform      {info['platform']}")
    print(f"  GIL enabled   {info['gil_enabled']}")
    print(f"  input         {INPUT} ({len(data):,} integers)")
    print(f"  iterations    {ITERATIONS}\n")

    # Measured the same way the Go side measures its input: the true cost of
    # holding these integers in the language's natural list type.
    from benchmark import measure_input_footprint
    input_mb = measure_input_footprint(lambda: load(INPUT))

    functions = [
        ("quick_sort", quick_sort),
        ("merge_sort", merge_sort),
        ("heap_sort", heap_sort),
        ("list.sort [stdlib]", list.sort),
    ]

    results = [
        benchmark(fn, data, ITERATIONS, label=label,
                  dataset="shared", input_mb=input_mb)
        for label, fn in functions
    ]

    print_table(results)

    print(f"\n  Python list of {len(data):,} ints   {input_mb:6.2f} MB")
    print(f"  Go []int64 equivalent        {len(data) * 8 / 1048576:6.2f} MB")

    os.makedirs("results", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"language": "python", "environment": info,
                   "results": [r.as_dict() for r in results]}, fh, indent=2)
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
