// main.go -- Go side of the Python vs Go benchmark.
//
// CS 660 Module Seven Assignment.
//
// Mirrors benchmark.py's methodology so the two sets of numbers are comparable:
//   * reads the SAME integers from shared_input.txt that the Python run uses
//   * makes a fresh copy of the input before every timed iteration, outside the
//     timed region, because quickSort and heapSort mutate their argument
//   * forces a GC before each iteration, outside the timed region, so a
//     collection cannot land mid-measurement
//   * runs one untimed warm-up, then reports mean / min / max / stdev
//   * validates every result against a known-sorted copy
//
// Usage: go run . --iterations 5 --input ../shared_input.txt --out ../results

package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"runtime"
	"runtime/debug"
	"sort"
	"strconv"
	"time"
)

const bytesPerMB = 1024 * 1024

type Result struct {
	Function    string  `json:"function"`
	N           int     `json:"n"`
	Iterations  int     `json:"iterations"`
	AvgTimeMS   float64 `json:"avg_time_ms"`
	MinTimeMS   float64 `json:"min_time_ms"`
	MaxTimeMS   float64 `json:"max_time_ms"`
	StdevTimeMS float64 `json:"stdev_time_ms"`
	AllocMB     float64 `json:"alloc_mb"`
	InputMB     float64 `json:"input_mb"`
	TotalMB     float64 `json:"total_mb"`
	Correct     bool    `json:"correct"`
}

func readInput(path string) []int64 {
	fh, err := os.Open(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "cannot open %s: %v\n", path, err)
		os.Exit(1)
	}
	defer fh.Close()

	values := make([]int64, 0, 100_000)
	scanner := bufio.NewScanner(fh)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		v, err := strconv.ParseInt(line, 10, 64)
		if err != nil {
			fmt.Fprintf(os.Stderr, "bad line %q: %v\n", line, err)
			os.Exit(1)
		}
		values = append(values, v)
	}
	return values
}

// benchmark mirrors benchmark.benchmark() from the Activity.
func benchmark(name string, fn func([]int64) []int64, data []int64,
	iterations int, expected []int64) Result {

	// --- correctness ------------------------------------------------------
	probe := make([]int64, len(data))
	copy(probe, data)
	produced := fn(probe)
	correct := true
	for i := range produced {
		if produced[i] != expected[i] {
			correct = false
			break
		}
	}

	// --- warm-up ----------------------------------------------------------
	warm := make([]int64, len(data))
	copy(warm, data)
	fn(warm)

	// --- timing pass ------------------------------------------------------
	samples := make([]float64, 0, iterations)
	for i := 0; i < iterations; i++ {
		work := make([]int64, len(data)) // untimed
		copy(work, data)                 // untimed
		runtime.GC()                     // untimed

		start := time.Now()
		fn(work)
		samples = append(samples, float64(time.Since(start).Nanoseconds())/1e6)
	}

	// --- allocation pass --------------------------------------------------
	// TotalAlloc is cumulative bytes allocated, so the delta across one call is
	// what the function itself allocated -- the closest analogue to what
	// tracemalloc reports on the Python side.
	work := make([]int64, len(data))
	copy(work, data)
	runtime.GC()
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	fn(work)
	runtime.ReadMemStats(&after)
	allocMB := float64(after.TotalAlloc-before.TotalAlloc) / bytesPerMB

	mean, min, max, stdev := stats(samples)
	inputMB := float64(len(data)*8) / bytesPerMB

	return Result{
		Function: name, N: len(data), Iterations: iterations,
		AvgTimeMS: mean, MinTimeMS: min, MaxTimeMS: max, StdevTimeMS: stdev,
		AllocMB: allocMB, InputMB: inputMB, TotalMB: inputMB + allocMB,
		Correct: correct,
	}
}

func stats(xs []float64) (mean, min, max, stdev float64) {
	min, max = xs[0], xs[0]
	sum := 0.0
	for _, x := range xs {
		sum += x
		if x < min {
			min = x
		}
		if x > max {
			max = x
		}
	}
	mean = sum / float64(len(xs))
	if len(xs) > 1 {
		v := 0.0
		for _, x := range xs {
			v += (x - mean) * (x - mean)
		}
		stdev = math.Sqrt(v / float64(len(xs)-1))
	}
	return
}

func main() {
	iterations := flag.Int("iterations", 5, "timed runs per measurement")
	input := flag.String("input", "../shared_input.txt", "shared integer input")
	out := flag.String("out", "../results", "output directory")
	flag.Parse()

	data := readInput(*input)
	expected := make([]int64, len(data))
	copy(expected, data)
	sort.Slice(expected, func(i, j int) bool { return expected[i] < expected[j] })

	fmt.Println("==============================================================")
	fmt.Println("GO BENCHMARK")
	fmt.Println("==============================================================")
	fmt.Printf("  go version    %s\n", runtime.Version())
	fmt.Printf("  GOOS/GOARCH   %s/%s\n", runtime.GOOS, runtime.GOARCH)
	fmt.Printf("  GOMAXPROCS    %d\n", runtime.GOMAXPROCS(0))
	fmt.Printf("  NumCPU        %d\n", runtime.NumCPU())
	fmt.Printf("  input         %s (%d integers)\n", *input, len(data))
	fmt.Printf("  iterations    %d\n\n", *iterations)

	maxDepth := 3 // 2^3 = 8 parallel branches
	results := []Result{
		benchmark("quick_sort", quickSort, data, *iterations, expected),
		benchmark("merge_sort", mergeSort, data, *iterations, expected),
		benchmark("heap_sort", heapSort, data, *iterations, expected),
		benchmark("merge_sort_parallel",
			func(d []int64) []int64 { return parallelMergeSort(d, maxDepth) },
			data, *iterations, expected),
		benchmark("sort.Slice [stdlib]", func(d []int64) []int64 {
			sort.Slice(d, func(i, j int) bool { return d[i] < d[j] })
			return d
		}, data, *iterations, expected),
	}

	fmt.Printf("%-22s %10s %8s %10s %10s %6s\n",
		"Function", "Avg (ms)", "Stdev", "Alloc (MB)", "Total (MB)", "OK")
	fmt.Println("---------------------------------------------------------------------------")
	for _, r := range results {
		ok := "yes"
		if !r.Correct {
			ok = "NO"
		}
		fmt.Printf("%-22s %10.2f %8.2f %10.2f %10.2f %6s\n",
			r.Function, r.AvgTimeMS, r.StdevTimeMS, r.AllocMB, r.TotalMB, ok)
	}

	// Process memory, for comparison against CPython's interpreter overhead.
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	fmt.Printf("\n  Go heap in use          %6.2f MB\n", float64(ms.HeapInuse)/bytesPerMB)
	fmt.Printf("  Go total heap reserved  %6.2f MB\n", float64(ms.HeapSys)/bytesPerMB)
	fmt.Printf("  input slice ([]int64)   %6.2f MB\n", float64(len(data)*8)/bytesPerMB)

	if err := os.MkdirAll(*out, 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	payload := map[string]any{
		"language": "go", "go_version": runtime.Version(),
		"gomaxprocs": runtime.GOMAXPROCS(0), "numcpu": runtime.NumCPU(),
		"results": results,
	}
	blob, _ := json.MarshalIndent(payload, "", "  ")
	path := *out + "/go_results.json"
	if err := os.WriteFile(path, blob, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("\nSaved to %s\n", path)
	_ = debug.SetGCPercent
}
