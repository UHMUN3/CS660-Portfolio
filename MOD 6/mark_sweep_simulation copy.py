"""
CS 660 -- Module Six Activity
Concurrent Memory Management Simulation: Mark-and-Sweep in a Threaded Runtime

Scenario
    A custom runtime for an embedded target with no built-in garbage collector.
    The runtime owns a small, fixed-size memory pool. Several application
    threads (mutators) concurrently create objects, link them together, and
    release them. A dedicated collector thread reclaims unreachable memory
    using a stop-the-world mark-and-sweep cycle.

Where each rubric criterion is implemented
    1. Simulation structure ......... HeapObject, MemoryPool, MutatorGate
    2. Multithreaded program ........ mutator_worker(), collector_worker(), main()
    3. Concurrent access ............ MutatorGate (phase control),
                                      MemoryPool._lock (data structure),
                                      EventLog._lock (output serialization)
    4. Mark-and-sweep cleanup ....... MemoryPool.collect()
    5. Runtime events ............... EventLog.emit() -- see the legend printed
                                      at startup for the full event taxonomy
    6. Challenges and solutions ..... discussed in the accompanying document;
                                      the design notes below flag each hazard
                                      at the point in the code where it arises

Run:  python3 mark_sweep_simulation.py
"""

from __future__ import annotations

import random
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuration -- small numbers keep the trace readable and force real
# memory pressure, so the allocator is observed failing and recovering.
# ---------------------------------------------------------------------------
POOL_CAPACITY = 256      # simulated bytes owned by the runtime
MUTATOR_THREADS = 3      # concurrent application threads
OPS_PER_MUTATOR = 5      # allocate/release steps performed by each thread
GC_INTERVAL = 0.04       # seconds between background collections
MASTER_SEED = 660        # fixed seed: object sizes are reproducible


# ---------------------------------------------------------------------------
# 5. RUNTIME EVENTS -- one lock-protected sink for all program output
# ---------------------------------------------------------------------------
class EventLog:
    """Thread-safe event printer.

    print() is not atomic across the several writes it performs, so
    concurrent threads can interleave fragments of different lines. A
    dedicated lock makes each event line indivisible. This is the smallest
    example in the program of the central lesson: shared mutable state --
    even stdout -- needs a mutex.
    """

    LEGEND = (
        ("THREAD",  "thread lifecycle and coordination"),
        ("ALLOC",   "pool grants bytes for a new object"),
        ("CREATE",  "object constructed and rooted in a thread's frame"),
        ("LINK",    "one object stores a reference to another"),
        ("DROP",    "thread releases a root reference (object may be garbage)"),
        ("OOM",     "allocation refused -- pool exhausted"),
        ("GC-STOP", "stop-the-world requested / mutators paused"),
        ("GC-MARK", "mark phase: tracing reachability from the root set"),
        ("RECLAIM", "sweep phase: unreachable object's memory reclaimed"),
        ("GC-DONE", "collection finished, pool utilization reported"),
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._t0 = time.perf_counter()

    def emit(self, tag: str, message: str) -> None:
        stamp = (time.perf_counter() - self._t0) * 1000.0
        who = threading.current_thread().name
        with self._lock:
            print(f"[{stamp:8.2f} ms] {who:<11} {tag:<8} {message}")

    def banner(self, title: str) -> None:
        with self._lock:
            print()
            print("=" * 88)
            print(f"  {title}")
            print("=" * 88)

    def print_legend(self) -> None:
        with self._lock:
            print("Event legend")
            for tag, meaning in self.LEGEND:
                print(f"    {tag:<8} {meaning}")
            print()


# ---------------------------------------------------------------------------
# 1. SIMULATION STRUCTURE -- the object model
# ---------------------------------------------------------------------------
@dataclass
class HeapObject:
    """One allocation in the simulated heap.

    `refs` is what makes this a genuine reachability problem rather than a
    flat list scan: an object held by no thread can still be live because
    another live object points at it, and two objects can point at each
    other while both are garbage. Reference counting cannot reclaim that
    second case; tracing collection can.
    """

    oid: int
    owner: str
    size: int
    refs: set[int] = field(default_factory=set)
    marked: bool = False

    def __repr__(self) -> str:  # keeps log lines short
        return f"obj#{self.oid}"


# ---------------------------------------------------------------------------
# 3. CONCURRENT ACCESS -- phase control between mutators and the collector
# ---------------------------------------------------------------------------
class MutatorGate:
    """A reader/writer gate that implements a "stop the world" mechanism.

    Mutator threads act as readers: multiple can operate simultaneously since the
    MemoryPool's lock already safeguards its internals from concurrent access. The
    collector functions as the writer: it requires the heap to be frozen, as a mutator
    that creates a new object during the mark phase could lead to that object being
    swept away as unreachable.

    Writer preference: once a collection is initiated, new mutators must wait.
    Without this, a continuous flow of allocations could indefinitely prevent the
    collector from running, causing the pool to become full.

    Lock ordering (to avoid deadlock): a thread should acquire the gate before the
    pool lock, but not the other way around. Additionally, a mutator must exit its
    critical section before requesting a collection — calling stop_the_world() while
    still counted as an active mutator would result in a deadlock.
    """

    def __init__(self, log: EventLog) -> None:
        self._cond = threading.Condition()
        self._active = 0          # mutators currently touching the heap
        self._stopping = False    # a collection is pending or running
        self._log = log

    @contextmanager
    def mutator(self):
        with self._cond:
            if self._stopping:
                self._log.emit("THREAD", "paused at safepoint -- collector holds the world")
            while self._stopping:
                self._cond.wait()
            self._active += 1
        try:
            yield
        finally:
            with self._cond:
                self._active -= 1
                if self._active == 0:
                    self._cond.notify_all()

    @contextmanager
    def stop_the_world(self):
        with self._cond:
            while self._stopping:          # serialize concurrent collectors
                self._cond.wait()
            self._stopping = True
            if self._active:
                self._log.emit("GC-STOP", f"waiting for {self._active} active mutator(s) to reach a safepoint")
            while self._active > 0:
                self._cond.wait()
        try:
            yield
        finally:
            with self._cond:
                self._stopping = False
                self._cond.notify_all()


# ---------------------------------------------------------------------------
# 1. SIMULATION STRUCTURE -- the heap itself
# 4. MARK-AND-SWEEP -- MemoryPool.collect()
# ---------------------------------------------------------------------------
class MemoryPool:
    """A fixed-capacity heap with an explicit, per-thread root set.

    `_roots[thread_name]` models that thread's stack frame: the handles it is
    actively holding. The union of all root sets is the GC root set. Every
    field below is shared mutable state reachable from several threads, so
    every method that reads or writes it holds `_lock`.
    """

    def __init__(self, capacity: int, log: EventLog) -> None:
        self.capacity = capacity
        self._log = log
        self._lock = threading.RLock()

        self._objects: dict[int, HeapObject] = {}
        self._roots: dict[str, set[int]] = defaultdict(set)
        self._used = 0
        self._next_oid = 1

        # Statistics. These are read-modify-write counters -- the classic
        # race condition -- and are only ever touched under _lock.
        self.total_allocated = 0
        self.total_reclaimed = 0
        self.bytes_reclaimed = 0
        self.peak_used = 0
        self.gc_cycles = 0
        self.oom_events = 0

    # -- allocation ---------------------------------------------------------
    def allocate(self, size: int) -> int | None:
        """Reserve `size` bytes and root the new object in the caller's frame.

        Returns the object id, or None if the pool cannot satisfy the request.
        The capacity check and the reservation must be one atomic step: if two
        threads each tested `used + size <= capacity` before either committed,
        both would pass and the pool would overflow.
        """
        owner = threading.current_thread().name
        with self._lock:
            if self._used + size > self.capacity:
                self.oom_events += 1
                self._log.emit(
                    "OOM",
                    f"request for {size}B refused -- only {self.capacity - self._used}B free",
                )
                return None

            oid = self._next_oid
            self._next_oid += 1
            self._objects[oid] = HeapObject(oid, owner, size)
            self._used += size
            self.peak_used = max(self.peak_used, self._used)
            self.total_allocated += 1
            self._log.emit(
                "ALLOC",
                f"reserved {size}B for obj#{oid}  ->  pool at {self._used}/{self.capacity}B",
            )

            self._roots[owner].add(oid)
            self._log.emit("CREATE", f"obj#{oid} constructed and rooted in {owner}'s frame")
            return oid

    # -- mutation -----------------------------------------------------------
    def link(self, parent: int, child: int) -> None:
        """Store a reference: `child` is now reachable through `parent`."""
        with self._lock:
            if parent in self._objects and child in self._objects:
                self._objects[parent].refs.add(child)
                self._log.emit("LINK", f"obj#{parent} now references obj#{child}")

    def drop_root(self, oid: int) -> None:
        """The calling thread stops holding `oid` -- it may now be garbage."""
        owner = threading.current_thread().name
        with self._lock:
            if oid in self._roots[owner]:
                self._roots[owner].discard(oid)
                self._log.emit("DROP", f"{owner} released obj#{oid} -- candidate for sweeping")

    def clear_roots(self) -> None:
        owner = threading.current_thread().name
        with self._lock:
            released = sorted(self._roots.pop(owner, set()))
            if released:
                pretty = ", ".join(f"obj#{o}" for o in released)
                self._log.emit("DROP", f"{owner} frame unwound, releasing {pretty}")

    # -- collection ---------------------------------------------------------
    def collect(self) -> None:
        """One mark-and-sweep cycle. Caller must hold the world stopped."""
        with self._lock:
            self.gc_cycles += 1
            cycle = self.gc_cycles
            before_objects, before_bytes = len(self._objects), self._used

            # ---- MARK: trace transitively from every thread's root set ----
            for obj in self._objects.values():
                obj.marked = False

            roots = sorted({oid for held in self._roots.values() for oid in held})
            shown = ", ".join(f"#{o}" for o in roots[:6]) if roots else "none"
            if len(roots) > 6:
                shown += f" +{len(roots) - 6}"
            self._log.emit("GC-MARK", f"cycle {cycle}: mark from {len(roots)} roots: {shown}")

            worklist = deque(roots)
            reachable = 0
            while worklist:
                obj = self._objects.get(worklist.popleft())
                if obj is None or obj.marked:
                    continue
                obj.marked = True
                reachable += 1
                worklist.extend(obj.refs)   # follow references, so held-by-object survives

            self._log.emit(
                "GC-MARK",
                f"cycle {cycle}: {reachable} of {before_objects} object(s) reachable",
            )

            # ---- SWEEP: everything unmarked is unreachable, so free it ----
            garbage = [obj for obj in self._objects.values() if not obj.marked]
            for obj in garbage:
                del self._objects[obj.oid]
                self._used -= obj.size
                self.total_reclaimed += 1
                self.bytes_reclaimed += obj.size
                self._log.emit(
                    "RECLAIM",
                    f"cycle {cycle}: swept obj#{obj.oid} ({obj.size}B, allocated by {obj.owner})",
                )

            freed = before_bytes - self._used
            self._log.emit(
                "GC-DONE",
                f"cycle {cycle}: freed {len(garbage)} obj / {freed}B  |  "
                f"{self._utilization_bar()}",
            )

    # -- reporting ----------------------------------------------------------
    def _utilization_bar(self, width: int = 14) -> str:
        filled = round(width * self._used / self.capacity)
        pct = 100.0 * self._used / self.capacity
        return f"[{'#' * filled}{'.' * (width - filled)}] {self._used:>3}/{self.capacity}B ({pct:4.1f}%)"

    def summary(self) -> list[str]:
        with self._lock:
            live = sorted(self._objects)
            return [
                f"Pool capacity ................ {self.capacity} B",
                f"Objects allocated ............ {self.total_allocated}",
                f"Objects reclaimed ............ {self.total_reclaimed}",
                f"Bytes reclaimed .............. {self.bytes_reclaimed} B",
                f"Peak utilization ............. {self.peak_used} B "
                f"({100.0 * self.peak_used / self.capacity:.1f}% of pool)",
                f"Collection cycles ............ {self.gc_cycles}",
                f"Allocation failures (OOM) .... {self.oom_events}",
                f"Live objects at shutdown ..... {len(live)} "
                f"{'(' + ', '.join(f'obj#{o}' for o in live) + ')' if live else '(pool fully drained)'}",
                f"Bytes still in use ........... {self._used} B",
            ]


# ---------------------------------------------------------------------------
# Collection driver -- used by both the collector thread and by a mutator
# that has just been refused an allocation.
# ---------------------------------------------------------------------------
def run_collection(pool: MemoryPool, gate: MutatorGate, log: EventLog, reason: str) -> None:
    log.emit("GC-STOP", f"collection requested ({reason})")
    with gate.stop_the_world():
        log.emit("GC-STOP", "world stopped -- heap is quiescent")
        pool.collect()
    log.emit("GC-STOP", "world resumed -- mutators released")


# ---------------------------------------------------------------------------
# 2. MULTITHREADED PROGRAM -- the application threads
# ---------------------------------------------------------------------------
def mutator_worker(pool: MemoryPool, gate: MutatorGate, log: EventLog, seed: int) -> None:
    """Simulates an application thread with a realistic object lifecycle mix.

    Each step allocates an object, then does one of three things with it:
      - keeps it rooted (stays live),
      - links it under an object this thread already holds and drops the root
        (survives collection only because the parent keeps it reachable),
      - pairs it with the previous object into a reference cycle and drops
        both roots (unreachable garbage that reference counting would leak).
    """
    rng = random.Random(seed)
    log.emit("THREAD", "started -- entering allocate/release loop")

    held: list[int] = []
    pending_cycle: int | None = None

    for step in range(1, OPS_PER_MUTATOR + 1):
        size = rng.choice([16, 24, 32, 40])

        # The gate is released before any collection is requested: a thread
        # counted as an active mutator can never stop the world.
        with gate.mutator():
            oid = pool.allocate(size)
            if oid is not None:
                # Initializing the new object's fields keeps this thread inside
                # the critical section briefly -- long enough that a collection
                # request arriving now must wait for the safepoint handshake.
                time.sleep(rng.uniform(0.002, 0.006))

        if oid is None:
            run_collection(pool, gate, log, "allocation failure -- reclaiming space")
            with gate.mutator():
                oid = pool.allocate(size)
            if oid is None:
                log.emit("THREAD", f"step {step}: still no space after collection -- skipping")
                continue

        # Choose this object's fate.
        if step == 3 and pending_cycle is not None:
            # Build A -> B -> A, then abandon both. Unreachable but each has
            # an incoming reference, so only tracing collection frees them.
            with gate.mutator():
                pool.link(pending_cycle, oid)
                pool.link(oid, pending_cycle)
                log.emit("THREAD", f"built reference cycle obj#{pending_cycle} <-> obj#{oid}, abandoning both")
                pool.drop_root(pending_cycle)
                pool.drop_root(oid)
            pending_cycle = None
        elif held and rng.random() < 0.5:
            # Reachable only through a parent this thread still holds.
            with gate.mutator():
                pool.link(held[-1], oid)
                pool.drop_root(oid)
        elif step == 2:
            pending_cycle = oid
            held.append(oid)
        else:
            held.append(oid)

        # Periodically let go of the oldest handle -- a frame going out of scope.
        if len(held) > 2:
            with gate.mutator():
                pool.drop_root(held.pop(0))

        time.sleep(rng.uniform(0.005, 0.02))   # simulate real work between allocations

    with gate.mutator():
        pool.clear_roots()
    log.emit("THREAD", "finished -- all frames unwound")


def collector_worker(pool: MemoryPool, gate: MutatorGate, log: EventLog,
                     shutdown: threading.Event) -> None:
    """Background collector: periodic stop-the-world mark-and-sweep."""
    log.emit("THREAD", f"collector online -- periodic sweep every {GC_INTERVAL * 1000:.0f} ms")
    while not shutdown.wait(GC_INTERVAL):
        run_collection(pool, gate, log, "periodic timer")
    log.emit("THREAD", "collector offline")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    log = EventLog()
    gate = MutatorGate(log)
    pool = MemoryPool(POOL_CAPACITY, log)

    log.banner("CS 660 Module Six Activity -- Concurrent Mark-and-Sweep Memory Simulation")
    print(f"Pool capacity   : {POOL_CAPACITY} B")
    print(f"Mutator threads : {MUTATOR_THREADS}  ({OPS_PER_MUTATOR} operations each)")
    print(f"Collector       : 1 background thread, stop-the-world, {GC_INTERVAL * 1000:.0f} ms interval")
    print()
    log.print_legend()

    shutdown = threading.Event()
    collector = threading.Thread(
        target=collector_worker, args=(pool, gate, log, shutdown), name="Collector", daemon=True
    )
    collector.start()

    mutators = [
        threading.Thread(
            target=mutator_worker,
            args=(pool, gate, log, MASTER_SEED + i),
            name=f"Mutator-{i + 1}",
        )
        for i in range(MUTATOR_THREADS)
    ]

    log.emit("THREAD", f"main launching {MUTATOR_THREADS} mutator thread(s)")
    for thread in mutators:
        thread.start()
    for thread in mutators:
        thread.join()
    log.emit("THREAD", "main joined all mutators -- roots are now empty")

    shutdown.set()
    collector.join(timeout=1.0)

    # Final collection with an empty root set: everything must be reclaimed.
    run_collection(pool, gate, log, "runtime shutdown -- final sweep")

    log.banner("Simulation Summary")
    for line in pool.summary():
        print(f"  {line}")
    print()


if __name__ == "__main__":
    main()
