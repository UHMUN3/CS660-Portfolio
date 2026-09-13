"""
CS 660 - Module Three Activity
Part One, Step 4: Correcting the Type Mismatches

Each function below is the repaired counterpart of a mismatch in
typing_mismatch.py. The repairs follow the three rules that Python's dynamic,
strongly typed model actually gives you:

    RULE 1  Convert explicitly. Python will not coerce for you, so state the
            conversion yourself (str(), float(), int(), f-strings).
    RULE 2  Validate at the boundary. Because no declaration is enforced, the
            function itself must reject values it cannot handle -- and it
            should fail with a message that names the caller's mistake.
    RULE 3  Annotate for the reader and the checker. Hints do not run, but they
            document intent and let an external static checker (mypy, pyright)
            find mismatches before execution.

RUN
    python3 typing_corrected.py
"""

from typing import List, Sequence, Union

Number = Union[int, float]


# ---------------------------------------------------------------------------
# FIX 1 - was: item + " x" + quantity   (str + int -> TypeError)
# ---------------------------------------------------------------------------
def build_receipt_line(item: str, quantity: int) -> str:
    """RULE 1: convert the int to text explicitly instead of relying on +."""
    return f"{item} x{quantity}"


# ---------------------------------------------------------------------------
# FIX 2 - was: price * (1 - percent)   with price arriving as a str
# ---------------------------------------------------------------------------
def apply_discount(price: Number, percent: float) -> float:
    """RULE 2: enforce at runtime what the annotation only claims."""
    price = _coerce_number(price, "price")
    percent = _coerce_number(percent, "percent")
    if not 0.0 <= percent <= 1.0:
        raise ValueError(f"percent must be between 0 and 1, got {percent!r}")
    return round(price * (1 - percent), 2)


def _coerce_number(value: object, name: str) -> float:
    """Accept int, float, or a numeric string; reject anything else clearly."""
    if isinstance(value, bool):
        # bool is a subclass of int in Python -- almost never intended here.
        raise TypeError(f"{name} must be numeric, got bool: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise TypeError(
                f"{name} must be numeric, got non-numeric str: {value!r}"
            ) from None
    raise TypeError(f"{name} must be numeric, got {type(value).__name__}")


# ---------------------------------------------------------------------------
# FIX 3 - was: label * times, which silently returned '777' instead of 21
# ---------------------------------------------------------------------------
def repeat_label(label: str, times: int) -> str:
    """RULE 2: the silent bug needs an explicit guard, since * never raised."""
    if not isinstance(label, str):
        raise TypeError(f"label must be str, got {type(label).__name__}")
    if not isinstance(times, int) or isinstance(times, bool):
        raise TypeError(f"times must be int, got {type(times).__name__}")
    return label * times


def add_quantities(a: Number, b: Number) -> float:
    """The arithmetic the caller of repeat_label('7', 3) actually wanted."""
    return _coerce_number(a, "a") + _coerce_number(b, "b")


# ---------------------------------------------------------------------------
# FIX 4 - was: len(records) / records[0] on a bare int
# ---------------------------------------------------------------------------
def first_id(records: Sequence[int]) -> int:
    """RULE 2 + RULE 3: check the shape, then the emptiness, then index."""
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise TypeError(
            f"records must be a sequence of int, got {type(records).__name__}"
        )
    if not records:
        raise ValueError("records is empty; there is no first id")
    return records[0]


# ---------------------------------------------------------------------------
# FIX 5 - was: "Order total: " + total, hidden inside a function never called
# ---------------------------------------------------------------------------
def format_total(total: Number) -> str:
    """RULE 1: explicit formatting. And this time the function is exercised,
    because in a dynamically typed language untested code is unchecked code."""
    return f"Order total: ${_coerce_number(total, 'total'):.2f}"


# ---------------------------------------------------------------------------
def demo(label: str, action) -> None:
    print(f"\n  {label}")
    try:
        result = action()
    except Exception as err:
        print(f"    -> RAISED {type(err).__name__}: {err}")
    else:
        print(f"    -> RETURNED {result!r}  (type: {type(result).__name__})")


def main() -> None:
    print("=" * 70)
    print("PART ONE - CORRECTED CODE, ALIGNED WITH PYTHON'S TYPING RULES")
    print("=" * 70)

    print("\n[A] The same calls that failed before now succeed")
    demo("1. build_receipt_line('widget', 3)",
         lambda: build_receipt_line("widget", 3))
    demo("2. apply_discount('19.99', 0.10)",
         lambda: apply_discount("19.99", 0.10))
    demo("3. add_quantities('7', 3)   [the intended arithmetic]",
         lambda: add_quantities("7", 3))
    demo("4. first_id([101, 102, 103])",
         lambda: first_id([101, 102, 103]))
    demo("5. format_total(42)   [formerly the unreachable mismatch]",
         lambda: format_total(42))

    print("\n[B] Genuinely bad input now fails loudly, at the boundary,")
    print("    with a message that names the offending argument")
    demo("6. apply_discount('nineteen', 0.10)",
         lambda: apply_discount("nineteen", 0.10))
    demo("7. repeat_label('7', '3')",
         lambda: repeat_label("7", "3"))
    demo("8. first_id(42)",
         lambda: first_id(42))
    demo("9. first_id([])",
         lambda: first_id([]))

    print("\n" + "=" * 70)
    print("Errors did not disappear -- they moved. They now surface at the")
    print("function boundary with the argument named, instead of deep inside")
    print("an expression with an operator-level message.")
    print("=" * 70)


if __name__ == "__main__":
    main()
