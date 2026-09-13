/*
 * csort.c -- A C quicksort that mirrors sorts.py's quick_sort exactly.
 *
 * CS 660 Module Seven Activity.
 *
 * Same algorithm as the Python version: median-of-three pivot, Hoare
 * partition, recursion into the smaller side and iteration on the larger.
 * Holding the algorithm fixed is the whole point -- whatever speed difference
 * shows up between this and sorts.quick_sort is attributable to the language
 * and its runtime, not to a smarter algorithm.
 *
 * Loaded from Python with ctypes, which needs no build system and no
 * CPython headers. It stands in for what Cython or a hand-written C
 * extension would produce.
 *
 * Build:
 *     cc -O2 -shared -fPIC -o libcsort.dylib csort.c      (macOS)
 *     cc -O2 -shared -fPIC -o libcsort.so    csort.c      (Linux)
 */

#include <stdlib.h>

typedef long long i64;

static void median_of_three(i64 *a, long low, long high) {
    long mid = low + (high - low) / 2;
    i64 t;
    if (a[mid] < a[low])  { t = a[low];  a[low]  = a[mid];  a[mid]  = t; }
    if (a[high] < a[low]) { t = a[low];  a[low]  = a[high]; a[high] = t; }
    if (a[high] < a[mid]) { t = a[mid];  a[mid]  = a[high]; a[high] = t; }
}

static long partition_hoare(i64 *a, long low, long high) {
    median_of_three(a, low, high);
    i64 pivot = a[low + (high - low) / 2];
    long i = low - 1;
    long j = high + 1;
    for (;;) {
        do { i++; } while (a[i] < pivot);
        do { j--; } while (a[j] > pivot);
        if (i >= j) return j;
        i64 t = a[i]; a[i] = a[j]; a[j] = t;
    }
}

static void quicksort_range(i64 *a, long low, long high) {
    while (low < high) {
        long split = partition_hoare(a, low, high);
        if (split - low < high - split) {
            quicksort_range(a, low, split);
            low = split + 1;
        } else {
            quicksort_range(a, split + 1, high);
            high = split;
        }
    }
}

/* Same algorithm as sorts.quick_sort, compiled. */
void c_quicksort_i64(i64 *a, long n) {
    if (n > 1) quicksort_range(a, 0, n - 1);
}

static int cmp_i64(const void *x, const void *y) {
    i64 a = *(const i64 *)x, b = *(const i64 *)y;
    return (a > b) - (a < b);
}

/* The C standard library's sort, for reference. */
void c_libc_qsort_i64(i64 *a, long n) {
    qsort(a, (size_t)n, sizeof(i64), cmp_i64);
}
