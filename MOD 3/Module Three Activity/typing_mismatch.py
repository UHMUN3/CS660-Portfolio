"""
CS 660 - Module Three Activity
Part One, Steps 1-3: Demonstrating Type Mismatches

TYPE SYSTEM UNDER TEST
    Python 3 is DYNAMICALLY typed and STRONGLY typed.
      - Dynamic: a name has no declared type. The type belongs to the object
        the name is bound to, and it is checked at the moment an operation
        executes -- not when the file is compiled.
      - Strong: Python refuses to silently coerce unrelated types. "5" + 5
        raises rather than guessing that you meant 10 or "55".
      - Gradual: type hints (PEP 484) may be written, but the interpreter
        treats them as metadata only. They are NOT enforced at runtime.

WHAT THIS FILE DOES
    Every mismatch below is syntactically legal, so the whole module compiles
    without complaint. Each failure is raised by the INTERPRETER at the moment
    the offending line runs. The harness catches each error so the program runs
    to completion and the full set of interpreter messages can be observed.

RUN
    python3 typing_mismatch.py
"""

import py_compile
import tempfile
from typing import List


# ---------------------------------------------------------------------------
# Test harness: runs one mismatch and reports what the interpreter did.
# ---------------------------------------------------------------------------
def attempt(label: str, action) -> None:
    """Execute `action`, reporting either its value or the exception raised."""
    print(f"\n  {label}")
    try:
        result = action()
    except Exception as err:
        print(f"    -> RAISED {type(err).__name__}: {err}")
    else:
        print(f"    -> RETURNED {result!r}  (type: {type(result).__name__})")


# ---------------------------------------------------------------------------
# MISMATCH 1 - Strong typing blocks implicit coercion.
# ---------------------------------------------------------------------------
def build_receipt_line(item, quantity):
    # Intended: "widget x3". Breaks when `quantity` is an int, because Python
    # will not implicitly convert int -> str to satisfy the + operator.
    return item + " x" + quantity


# ---------------------------------------------------------------------------
# MISMATCH 2 - Type hints are documentation, not enforcement.
# ---------------------------------------------------------------------------
def apply_discount(price: float, percent: float) -> float:
    # The annotations claim float. Nothing in CPython checks that claim, so a
    # caller may pass a str and the mismatch surfaces only inside the body.
    return price * (1 - percent)


# ---------------------------------------------------------------------------
# MISMATCH 3 - A mismatch that does NOT raise: the silent bug.
# ---------------------------------------------------------------------------
def repeat_label(label: str, times: int) -> str:
    # str * int is a legal, well-defined operation in Python. If `label` is a
    # str and `times` is an int, this returns a value even when the caller
    # meant arithmetic. Strong typing does not help here -- the operator is
    # simply overloaded for these operand types.
    return label * times


# ---------------------------------------------------------------------------
# MISMATCH 4 - Wrong type reaches an operation that has no meaning for it.
# ---------------------------------------------------------------------------
def first_id(records: List[int]) -> int:
    # Assumes a subscriptable, sized sequence. An int satisfies neither.
    print(f"    (record count: {len(records)})")
    return records[0]


# ---------------------------------------------------------------------------
# MISMATCH 5 - Never called, therefore never detected.
# ---------------------------------------------------------------------------
def unreachable_mismatch():
    # This is a guaranteed TypeError, yet the module still imports, compiles,
    # and runs cleanly. Nothing checks it because nothing executes it. This is
    # the single clearest illustration of dynamic typing's cost.
    total = 42
    return "Order total: " + total


# ---------------------------------------------------------------------------
# COMPILE-TIME vs RUNTIME evidence (Step 5 support)
# ---------------------------------------------------------------------------
def show_compile_stage() -> None:
    """Prove the type errors above survive compilation untouched."""
    print("\n[C] COMPILE STAGE")

    # This source contains a certain TypeError. It compiles anyway.
    typed_badly = 'x = "total: " + 42\n'
    try:
        compile(typed_badly, "<mismatch>", "exec")
        print('    compile(\'x = "total: " + 42\') -> SUCCESS (no type check)')
    except Exception as err:
        print(f"    unexpected: {type(err).__name__}: {err}")

    # A SYNTAX error, by contrast, is rejected before anything executes.
    written_badly = 'x = = 42\n'
    try:
        compile(written_badly, "<syntax>", "exec")
        print("    compile('x = = 42') -> SUCCESS")
    except SyntaxError as err:
        print(f"    compile('x = = 42') -> SyntaxError: {err.msg}")

    # The entire module compiles to bytecode despite containing five mismatches.
    with tempfile.NamedTemporaryFile(suffix=".pyc", delete=False) as tmp:
        py_compile.compile(__file__, cfile=tmp.name, doraise=True)
    print("    py_compile of this whole module -> SUCCESS (bytecode written)")
    print("    CONCLUSION: the compile stage validates GRAMMAR, not TYPES.")


# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 70)
    print("PART ONE - TYPE MISMATCHES UNDER PYTHON'S DYNAMIC TYPE SYSTEM")
    print("=" * 70)

    print("\n[R] RUNTIME STAGE")

    attempt(
        "1. str + int  ->  build_receipt_line('widget', 3)",
        lambda: build_receipt_line("widget", 3),
    )

    attempt(
        "2. annotation ignored  ->  apply_discount('19.99', 0.10)",
        lambda: apply_discount("19.99", 0.10),
    )

    attempt(
        "3. silent mismatch  ->  repeat_label('7', 3)   [expected 21]",
        lambda: repeat_label("7", 3),
    )

    attempt(
        "4. int used as list  ->  first_id(42)",
        lambda: first_id(42),
    )

    print("\n  5. unreachable_mismatch() is defined but never called")
    print("    -> NO ERROR. The guaranteed TypeError is never discovered.")

    show_compile_stage()

    print("\n" + "=" * 70)
    print("Module reached the end. Four mismatches raised at runtime, one was")
    print("never detected, and zero were caught before execution began.")
    print("=" * 70)


if __name__ == "__main__":
    main()
