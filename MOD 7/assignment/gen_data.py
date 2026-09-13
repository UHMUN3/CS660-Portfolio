"""Generate the shared input both languages will sort.

CS 660 Module Seven Assignment.

Go and Python have different pseudorandom generators, so "same seed" would not
mean "same data". Writing the integers to a file once and having both languages
read it removes that variable entirely: the two runtimes sort identical bytes.
"""
import random

N = 100_000
SEED = 660
OUT = "shared_input.txt"

rng = random.Random(SEED)
values = [rng.randint(0, 10**9) for _ in range(N)]

with open(OUT, "w") as fh:
    fh.write("\n".join(map(str, values)))

print(f"wrote {len(values):,} integers to {OUT}")
print(f"  first 5: {values[:5]}")
print(f"  checksum (sum): {sum(values)}")
