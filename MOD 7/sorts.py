"""
sorts.py -- Pure-Python implementations of quick sort, merge sort, and heap sort.

CS 660 Module Seven Activity.

Every public sort here takes a list and returns the sorted list, so all three
share one interface and can be handed to the benchmarking harness
interchangeably:

    sort_function(data: list) -> list

Implementation notes that matter for the benchmark results:

* quick_sort and heap_sort sort IN PLACE and return the same list object.
  Their extra memory is O(log n) and O(1) respectively.
* merge_sort is NOT in place. It returns a new list and allocates heavily,
  which is exactly the behavior the memory portion of this activity examines.
* Everything is written in pure Python on purpose. The point of the activity
  is to measure what the CPython interpreter costs, so calling list.sort()
  (which is Timsort implemented in C) would defeat it. list.sort() is still
  benchmarked separately in run_benchmarks.py as a reference baseline.
"""

__all__ = ["quick_sort", "merge_sort", "heap_sort"]


# ---------------------------------------------------------------------------
# Quick sort -- in place, median-of-three pivot, Hoare partition
# ---------------------------------------------------------------------------

def quick_sort(data):
    """Sort `data` in place and return it.

    Average case O(n log n) time, O(log n) stack space.

    Two defenses against quick sort's classic worst case are built in, because
    a naive version blows CPython's 1000-frame recursion limit long before it
    finishes 100,000 already-sorted elements:

    1. Median-of-three pivot selection, so sorted and reverse-sorted input
       become the best case instead of the O(n^2) worst case.
    2. Tail-call elimination on the larger partition, which bounds the actual
       recursion depth at O(log n) no matter how the pivots fall.
    """
    _quick_sort(data, 0, len(data) - 1)
    return data


def _quick_sort(data, low, high):
    # Loop on the larger side, recurse into the smaller side. This is what
    # keeps the stack at O(log n).
    while low < high:
        split = _partition(data, low, high)
        if split - low < high - split:
            _quick_sort(data, low, split)
            low = split + 1
        else:
            _quick_sort(data, split + 1, high)
            high = split


def _partition(data, low, high):
    """Hoare partition. Returns j such that data[low:j+1] <= data[j+1:high+1]."""
    _median_of_three(data, low, high)
    pivot = data[(low + high) // 2]

    i = low - 1
    j = high + 1
    while True:
        i += 1
        while data[i] < pivot:
            i += 1
        j -= 1
        while data[j] > pivot:
            j -= 1
        if i >= j:
            return j
        data[i], data[j] = data[j], data[i]


def _median_of_three(data, low, high):
    """Order data[low] <= data[mid] <= data[high], leaving the median at mid."""
    mid = (low + high) // 2
    if data[mid] < data[low]:
        data[low], data[mid] = data[mid], data[low]
    if data[high] < data[low]:
        data[low], data[high] = data[high], data[low]
    if data[high] < data[mid]:
        data[mid], data[high] = data[high], data[mid]


# ---------------------------------------------------------------------------
# Merge sort -- top-down, stable, allocates new lists
# ---------------------------------------------------------------------------

def merge_sort(data):
    """Return a new sorted list. `data` is left untouched.

    O(n log n) time in every case, and O(n log n) cumulative allocation: each
    level of the recursion slices fresh lists, and _merge builds another list
    on the way back up. Those allocations are the reason merge sort's
    tracemalloc peak dwarfs the other two.
    """
    if len(data) <= 1:
        return list(data)

    mid = len(data) // 2
    left = merge_sort(data[:mid])
    right = merge_sort(data[mid:])
    return _merge(left, right)


def _merge(left, right):
    """Merge two sorted lists into a new sorted list. Stable."""
    merged = []
    append = merged.append          # bound method lookup hoisted out of the loop
    i = j = 0
    n_left, n_right = len(left), len(right)

    while i < n_left and j < n_right:
        if left[i] <= right[j]:     # <= keeps the merge stable
            append(left[i])
            i += 1
        else:
            append(right[j])
            j += 1

    # One side is exhausted; the other is already sorted, so bulk-copy it.
    if i < n_left:
        merged.extend(left[i:])
    if j < n_right:
        merged.extend(right[j:])
    return merged


# ---------------------------------------------------------------------------
# Heap sort -- in place, binary max-heap
# ---------------------------------------------------------------------------

def heap_sort(data):
    """Sort `data` in place and return it.

    O(n log n) time in every case and O(1) extra space, which makes it the
    memory floor of the three. It is also the slowest of the three in practice:
    sift-down jumps between indices 2i+1 and 2i+2, so it has the worst cache
    locality, and every comparison still pays full interpreter overhead.
    """
    n = len(data)

    # Build a max-heap bottom-up: O(n), not O(n log n).
    for root in range(n // 2 - 1, -1, -1):
        _sift_down(data, root, n)

    # Repeatedly move the max to the end and shrink the heap.
    for end in range(n - 1, 0, -1):
        data[0], data[end] = data[end], data[0]
        _sift_down(data, 0, end)

    return data


def _sift_down(data, root, size):
    """Push data[root] down into its correct slot within the heap of `size`.

    Uses the "hole" technique: carry the item in a local and shift children up,
    then write the item once at the end. That is one write per level instead of
    the three-write swap a textbook version does.
    """
    item = data[root]
    while True:
        child = 2 * root + 1
        if child >= size:
            break
        # Pick the larger of the two children.
        right = child + 1
        if right < size and data[right] > data[child]:
            child = right
        if data[child] <= item:
            break
        data[root] = data[child]
        root = child
    data[root] = item
