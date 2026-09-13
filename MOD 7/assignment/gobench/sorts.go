// sorts.go -- Quick sort, merge sort, and heap sort in Go.
//
// CS 660 Module Seven Assignment.
//
// These are deliberate line-for-line ports of sorts.py from the Module Seven
// Activity. Same pivot strategy, same partition scheme, same loop structure,
// same recursion discipline. Holding the algorithm constant is the entire
// point: whatever difference the benchmark reports is attributable to the
// language and its runtime, not to a cleverer implementation on either side.

package main

// ---------------------------------------------------------------------------
// Quick sort -- in place, median-of-three pivot, Hoare partition
// ---------------------------------------------------------------------------

func quickSort(data []int64) []int64 {
	quickSortRange(data, 0, len(data)-1)
	return data
}

func quickSortRange(data []int64, low, high int) {
	// Recurse into the smaller side, loop on the larger. Go grows goroutine
	// stacks dynamically so this is not strictly required as it is in CPython,
	// but it is kept so the two implementations match exactly.
	for low < high {
		split := partition(data, low, high)
		if split-low < high-split {
			quickSortRange(data, low, split)
			low = split + 1
		} else {
			quickSortRange(data, split+1, high)
			high = split
		}
	}
}

func partition(data []int64, low, high int) int {
	medianOfThree(data, low, high)
	pivot := data[(low+high)/2]

	i := low - 1
	j := high + 1
	for {
		i++
		for data[i] < pivot {
			i++
		}
		j--
		for data[j] > pivot {
			j--
		}
		if i >= j {
			return j
		}
		data[i], data[j] = data[j], data[i]
	}
}

func medianOfThree(data []int64, low, high int) {
	mid := (low + high) / 2
	if data[mid] < data[low] {
		data[low], data[mid] = data[mid], data[low]
	}
	if data[high] < data[low] {
		data[low], data[high] = data[high], data[low]
	}
	if data[high] < data[mid] {
		data[mid], data[high] = data[high], data[mid]
	}
}

// ---------------------------------------------------------------------------
// Merge sort -- top-down, stable, allocates new slices
// ---------------------------------------------------------------------------

func mergeSort(data []int64) []int64 {
	if len(data) <= 1 {
		out := make([]int64, len(data))
		copy(out, data)
		return out
	}
	mid := len(data) / 2
	left := mergeSort(data[:mid])
	right := mergeSort(data[mid:])
	return merge(left, right)
}

func merge(left, right []int64) []int64 {
	merged := make([]int64, 0, len(left)+len(right))
	i, j := 0, 0
	for i < len(left) && j < len(right) {
		if left[i] <= right[j] { // <= keeps the merge stable
			merged = append(merged, left[i])
			i++
		} else {
			merged = append(merged, right[j])
			j++
		}
	}
	merged = append(merged, left[i:]...)
	merged = append(merged, right[j:]...)
	return merged
}

// ---------------------------------------------------------------------------
// Parallel merge sort -- the comparison CPython cannot make
// ---------------------------------------------------------------------------

// parallelMergeSort forks goroutines until depth runs out, then falls back to
// the sequential version. This exists to demonstrate something the Python side
// structurally cannot do: CPython's global interpreter lock prevents pure-Python
// bytecode from executing on more than one core at a time, so the identical
// divide-and-conquer structure yields no speedup there. Go's scheduler maps
// goroutines onto GOMAXPROCS OS threads and the work actually runs in parallel.
func parallelMergeSort(data []int64, depth int) []int64 {
	if depth <= 0 || len(data) < 2048 {
		return mergeSort(data)
	}
	mid := len(data) / 2

	var left []int64
	done := make(chan struct{})
	go func() {
		left = parallelMergeSort(data[:mid], depth-1)
		close(done)
	}()
	right := parallelMergeSort(data[mid:], depth-1)
	<-done

	return merge(left, right)
}

// ---------------------------------------------------------------------------
// Heap sort -- in place, binary max-heap
// ---------------------------------------------------------------------------

func heapSort(data []int64) []int64 {
	n := len(data)
	for root := n/2 - 1; root >= 0; root-- {
		siftDown(data, root, n)
	}
	for end := n - 1; end > 0; end-- {
		data[0], data[end] = data[end], data[0]
		siftDown(data, 0, end)
	}
	return data
}

func siftDown(data []int64, root, size int) {
	item := data[root]
	for {
		child := 2*root + 1
		if child >= size {
			break
		}
		if right := child + 1; right < size && data[right] > data[child] {
			child = right
		}
		if data[child] <= item {
			break
		}
		data[root] = data[child]
		root = child
	}
	data[root] = item
}
