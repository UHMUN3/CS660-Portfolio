"""
benchmark.py -- A small, reusable benchmarking harness for Python callables.

CS 660 Module Seven Activity.

The harness is deliberately generic: it knows nothing about sorting. It takes
any callable plus an input list and reports how long the callable takes and how
much memory it allocates. Any engineer on the team can reuse it by importing
one function.

    from benchmark import benchmark, print_table, write_csv, write_json

    result  = benchmark(my_sort, my_data, iterations=10)
    print_table([result])
    write_csv([result], "results.csv")

Rubric requirements and where each is satisfied
-----------------------------------------------
A. Accepts a sort function and an input list as parameters
       -> benchmark(sort_function, data, ...)
B. Runs the function a configurable number of iterations
       -> the `iterations` parameter (default 5)
C. Measures average execution time with time.perf_counter
       -> _time_pass(), which also reports min / max / stdev
D. Captures peak memory usage with tracemalloc
       -> _memory_pass()
E. Outputs the collected results to the console or saves them to a file
       -> print_table() for the console, write_csv() and write_json() for files

Three measurement decisions worth calling out
----------------------------------------------
1. Timing and memory are collected in SEPARATE passes. tracemalloc hooks every
   allocation the interpreter makes and inflates runtime several-fold, so
   timing anything while it is running measures the profiler, not the code.

2. Every iteration gets a FRESH COPY of the input, and the copy is made outside
   the timed region. quick_sort and heap_sort mutate their argument, so
   without this the second iteration would be timing an already-sorted list --
   a completely different workload.

3. gc.collect() runs before each timed iteration, outside the timed region, so
   a garbage collection pass triggered by earlier work cannot land in the
   middle of a measurement and show up as a phantom outlier.
"""

from __future__ import annotations

import csv
import gc
import json
import platform
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass, asdict, field

__all__ = [
    "BenchmarkResult",
    "benchmark",
    "benchmark_suite",
    "measure_input_footprint",
    "print_table",
    "write_csv",
    "write_json",
]

_BYTES_PER_MB = 1024 * 1024


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    """One measured (function, dataset) pair."""

    function: str
    dataset: str
    n: int
    iterations: int

    # Timing, in milliseconds.
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    stdev_time_ms: float

    # Memory, in megabytes.
    peak_alloc_mb: float        # allocated by the function itself
    input_mb: float             # allocated by the input list + its integers
    peak_total_mb: float        # input_mb + peak_alloc_mb

    correct: bool               # output verified against sorted()
    notes: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Memory helpers
# ---------------------------------------------------------------------------

def measure_input_footprint(factory) -> float:
    """Return the megabytes a dataset costs to build.

    `factory` is a zero-argument callable that returns the dataset.

    tracemalloc only counts allocations made after it starts, so the dataset
    has to be built under tracing to be counted at all. This number is the
    other half of the memory picture: benchmark() reports what the sort
    allocates, and this reports what the data itself already costs before the
    sort is even called.
    """
    gc.collect()
    tracemalloc.start()
    try:
        data = factory()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    del data
    gc.collect()
    return peak / _BYTES_PER_MB


def _memory_pass(function, data, copy_function=list) -> float:
    """Return the peak megabytes `function` allocates while processing `data`.

    The working copy is made before tracing starts so the copy is not counted
    against the function -- we want the function's own allocations, not ours.
    """
    work = copy_function(data)
    gc.collect()

    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        function(work)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    del work
    gc.collect()
    return peak / _BYTES_PER_MB


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------

def _time_pass(function, data, iterations, warmup, copy_function=list):
    """Return a list of per-iteration wall times in seconds.

    time.perf_counter is the right clock here: it is monotonic, it has the
    highest resolution the platform offers, and unlike time.process_time it
    includes time the process spends blocked -- which is what a stakeholder
    holding a 400 ms budget actually cares about.
    """
    for _ in range(warmup):
        function(copy_function(data))

    samples = []
    for _ in range(iterations):
        work = copy_function(data)  # untimed: fresh input for every iteration
        gc.collect()               # untimed: no phantom GC pause mid-measurement
        start = time.perf_counter()
        function(work)
        samples.append(time.perf_counter() - start)
        del work

    return samples


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def benchmark(
    sort_function,
    data,
    iterations: int = 5,
    *,
    label: str | None = None,
    dataset: str = "unnamed",
    input_mb: float = 0.0,
    warmup: int = 1,
    measure_memory: bool = True,
    validate: bool = True,
    copy_function=list,
    validator=None,
) -> BenchmarkResult:
    """Benchmark `sort_function` against `data` and return a BenchmarkResult.

    Parameters
    ----------
    sort_function : callable
        Any callable taking one list. If it returns a list, that return value
        is what gets validated; if it returns None, the mutated input is
        validated instead. This lets in-place sorts, list-returning sorts, and
        list.sort itself all share one code path.
    data : list
        The input. Never mutated -- every iteration works on a copy.
    iterations : int
        How many timed runs to average. Configurable per the requirements.
    label : str, optional
        Display name. Defaults to the callable's __name__.
    dataset : str
        Display name for the input distribution, e.g. "random" or "sorted".
    input_mb : float
        Megabytes the dataset itself occupies, from measure_input_footprint().
        Carried through so the report can show total footprint, not just the
        function's incremental allocation.
    warmup : int
        Untimed runs before measurement, to page in code and warm caches.
    measure_memory : bool
        Set False to skip the tracemalloc pass on very large or slow inputs.
    validate : bool
        Verify the output actually equals sorted(data). A fast wrong answer is
        not a result.
    copy_function : callable
        How to make a fresh working copy of `data` for each iteration. Defaults
        to `list`. Override it for inputs that are not Python lists -- e.g.
        numpy.copy for an ndarray -- which is what lets this same harness
        benchmark the mitigation options in mitigations.py rather than needing
        a second harness written just for them.
    validator : callable, optional
        Custom correctness check, called as validator(produced, data). Needed
        for outputs that do not compare cleanly with == against a Python list,
        such as numpy arrays.
    """
    if not callable(sort_function):
        raise TypeError("sort_function must be callable")
    if not hasattr(data, "__len__"):
        raise TypeError("data must be a sized sequence")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    name = label or getattr(sort_function, "__name__", repr(sort_function))

    # --- correctness ------------------------------------------------------
    correct = True
    if validate:
        probe = copy_function(data)
        returned = sort_function(probe)
        produced = probe if returned is None else returned
        if validator is not None:
            correct = bool(validator(produced, data))
        else:
            correct = list(produced) == sorted(data)
        del probe, returned, produced
        gc.collect()

    # --- pass 1: timing (no tracemalloc running) --------------------------
    samples = _time_pass(sort_function, data, iterations, warmup, copy_function)

    # --- pass 2: memory (separate, so it cannot distort pass 1) -----------
    peak_alloc_mb = (_memory_pass(sort_function, data, copy_function)
                     if measure_memory else 0.0)

    return BenchmarkResult(
        function=name,
        dataset=dataset,
        n=len(data),
        iterations=iterations,
        avg_time_ms=statistics.fmean(samples) * 1000,
        min_time_ms=min(samples) * 1000,
        max_time_ms=max(samples) * 1000,
        stdev_time_ms=(statistics.stdev(samples) * 1000) if len(samples) > 1 else 0.0,
        peak_alloc_mb=peak_alloc_mb,
        input_mb=input_mb,
        peak_total_mb=input_mb + peak_alloc_mb,
        correct=correct,
    )


def benchmark_suite(functions, datasets, iterations: int = 5, **kwargs):
    """Benchmark every function against every dataset.

    `functions` is an iterable of callables or (label, callable) pairs.

    `datasets` is a mapping of {name: factory} or an iterable of
    (name, factory) pairs, where each factory is a zero-argument callable that
    BUILDS the dataset. Factories rather than plain lists, because the input's
    true memory cost can only be measured while the data is being constructed:
    copying an existing list of integers allocates a new pointer array but
    reuses the very int objects that account for most of the footprint, so
    measuring a copy would under-report the input by roughly 4x.

    A plain list is still accepted for convenience, but its reported input_mb
    then covers only the list object itself.

    Returns a flat list of BenchmarkResult.
    """
    if hasattr(datasets, "items"):
        datasets = list(datasets.items())

    normalized = []
    for entry in functions:
        if isinstance(entry, tuple):
            normalized.append(entry)
        else:
            normalized.append((getattr(entry, "__name__", repr(entry)), entry))

    results = []
    for ds_name, ds_source in datasets:
        if callable(ds_source):
            footprint = measure_input_footprint(ds_source)
            ds_data = ds_source()
        else:
            ds_data = ds_source
            footprint = sys.getsizeof(ds_data) / _BYTES_PER_MB

        for label, fn in normalized:
            results.append(
                benchmark(fn, ds_data, iterations,
                          label=label, dataset=ds_name,
                          input_mb=footprint, **kwargs)
            )
        del ds_data
        gc.collect()
    return results


# ---------------------------------------------------------------------------
# Output: console
# ---------------------------------------------------------------------------

def print_table(results, title=None, budget_ms=None, budget_mb=None, stream=sys.stdout):
    """Print results as an aligned console table.

    If budget_ms / budget_mb are supplied, a PASS/FAIL verdict column is added
    so the table answers the stakeholders' question directly instead of leaving
    the reader to compare numbers by hand.
    """
    if not results:
        print("(no results)", file=stream)
        return

    show_verdict = budget_ms is not None or budget_mb is not None

    headers = ["Function", "Dataset", "n", "Iter",
               "Avg (ms)", "Stdev", "Peak alloc (MB)", "Total mem (MB)", "OK"]
    if show_verdict:
        headers.append("Verdict")

    rows = []
    for r in results:
        row = [
            r.function,
            r.dataset,
            f"{r.n:,}",
            str(r.iterations),
            f"{r.avg_time_ms:,.2f}",
            f"{r.stdev_time_ms:,.2f}",
            f"{r.peak_alloc_mb:,.2f}",
            f"{r.peak_total_mb:,.2f}",
            "yes" if r.correct else "NO",
        ]
        if show_verdict:
            row.append(_verdict(r, budget_ms, budget_mb))
        rows.append(row)

    widths = [max(len(h), *(len(row[i]) for row in rows))
              for i, h in enumerate(headers)]

    if title:
        print(f"\n{title}", file=stream)
        print("=" * sum(w + 2 for w in widths), file=stream)

    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)), file=stream)
    print("  ".join("-" * w for w in widths), file=stream)
    for row in rows:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)), file=stream)


def _verdict(result, budget_ms, budget_mb):
    failures = []
    if budget_ms is not None and result.avg_time_ms > budget_ms:
        failures.append("TIME")
    if budget_mb is not None and result.peak_total_mb > budget_mb:
        failures.append("MEM")
    return "PASS" if not failures else "FAIL:" + "+".join(failures)


# ---------------------------------------------------------------------------
# Output: files
# ---------------------------------------------------------------------------

def write_csv(results, path):
    """Save results to CSV -- the format a stakeholder can open in Excel."""
    if not results:
        return path
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].as_dict()))
        writer.writeheader()
        for r in results:
            writer.writerow(r.as_dict())
    return path


def write_json(results, path, include_environment=True):
    """Save results to JSON, with the machine details that make them reproducible.

    A timing number without the hardware and interpreter it came from is not
    reusable evidence, so the environment block travels with the data.
    """
    payload = {"results": [r.as_dict() for r in results]}
    if include_environment:
        payload["environment"] = environment_info()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def environment_info() -> dict:
    """Describe the machine and interpreter the measurements came from."""
    return {
        "python_version": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
        "int_object_bytes": sys.getsizeof(10**6),
        "pointer_bytes": sys.getsizeof([]) and 8,
        "recursion_limit": sys.getrecursionlimit(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
