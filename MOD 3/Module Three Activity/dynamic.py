"""
CS 660 - Module Three Activity
Part Two, Steps 8 and 9: Simulating Dynamic Scoping

Python has no dynamic scoping, so it must be simulated. This file replaces
Python's LEGB name resolution with an explicit environment stack:

    * Every function call PUSHES a frame holding the names it binds.
    * Reading a free name WALKS THE STACK from the most recent call outward
      and takes the first frame that holds the name.
    * Returning POPS the frame, so the binding disappears for later callers.

The difference from lexical.py is exactly one word: lexical resolution walks
the chain of functions a name is WRITTEN inside; dynamic resolution walks the
chain of functions that are currently RUNNING. Where those two chains coincide
the models agree (Examples 1-4). Where they diverge the models disagree
(Example 5), and a closure that outlives its caller breaks outright (Example 3b).

RUN
    python3 dynamic.py
"""

import contextlib
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# The simulated dynamic environment: a stack of frames, innermost call last.
# ---------------------------------------------------------------------------
_dyn_stack: List[Dict[str, Any]] = []


@contextlib.contextmanager
def dyn_frame(**bindings: Any):
    """Push a call frame on entry, pop it on exit -- even if an error is raised.

    The pop is what makes this DYNAMIC: a binding is visible for the duration
    of the call that created it and to everything that call reaches, then it
    is gone. Lexical bindings, by contrast, can outlive their call inside a
    closure (see lexical.py, example_3).
    """
    _dyn_stack.append(dict(bindings))
    try:
        yield
    finally:
        _dyn_stack.pop()


def dyn_get(name: str) -> Any:
    """Resolve a free name against the CALL stack, newest frame first."""
    for frame in reversed(_dyn_stack):        # reversed == innermost caller out
        if name in frame:
            return frame[name]
    raise NameError(
        f"{name!r} is not bound anywhere in the current call stack "
        f"(depth {len(_dyn_stack)})"
    )


def dyn_set(name: str, value: Any) -> None:
    """Rebind the nearest existing binding -- the dynamic analogue of nonlocal."""
    for frame in reversed(_dyn_stack):
        if name in frame:
            frame[name] = value
            return
    raise NameError(f"cannot assign to unbound dynamic name {name!r}")


def dyn_bind(name: str, value: Any) -> None:
    """Create/overwrite a binding in the CURRENT frame only (shadowing)."""
    _dyn_stack[-1][name] = value


def stack_view() -> str:
    """Render the live stack, so the trace is visible in the program output."""
    return " | ".join(str(frame) for frame in _dyn_stack) or "(empty)"


# ---------------------------------------------------------------------------
# EXAMPLE 1 - one level. Call chain matches nesting, so the answer matches too.
# ---------------------------------------------------------------------------
def example_1():
    with dyn_frame(x="outer"):            # PUSH {'x': 'outer'}
        def inner():
            with dyn_frame():             # PUSH {} -- inner binds nothing
                # TRACE  look for 'x': top frame {} misses, next frame holds
                #        'x' = "outer" -> HIT. Same result as lexical, but the
                #        reason differs: found via the CALLER, not via nesting.
                print(f"Inner sees: {dyn_get('x')}")
            # POP
        inner()
        print(f"Outer has: {dyn_get('x')}")
    # POP -> 'x' no longer exists anywhere


# ---------------------------------------------------------------------------
# EXAMPLE 2 - two levels. The nearest CALLER wins, as the nearest ENCLOSING
# scope did lexically. Identical output, different mechanism.
# ---------------------------------------------------------------------------
def example_2():
    with dyn_frame(x=10):                 # PUSH {'x': 10}
        def middle():
            with dyn_frame(x=20):         # PUSH {'x': 20} -- shadows, not
                                          # overwrites: two frames now hold 'x'
                def inner():
                    with dyn_frame():     # PUSH {}
                        # TRACE  stack is [{'x':10}, {'x':20}, {}].
                        #        Search newest-first: {} miss, {'x':20} HIT.
                        #        The 10 underneath is never reached.
                        print(f"Inner sees: {dyn_get('x')}")
                inner()
                print(f"Middle has: {dyn_get('x')}")   # 20, middle's frame
        middle()
        # middle's frame has been popped, uncovering the original binding
        print(f"Outer has: {dyn_get('x')}")            # 10, restored


# ---------------------------------------------------------------------------
# EXAMPLE 3 - dyn_set is the dynamic analogue of nonlocal.
# ---------------------------------------------------------------------------
def increment():
    """Free variable 'count' is resolved against whoever is calling."""
    with dyn_frame():
        # TRACE  dyn_set walks outward to the nearest frame holding 'count'
        #        and rebinds it in place -- no copy is made.
        dyn_set("count", dyn_get("count") + 1)
        return dyn_get("count")


def get_counter():
    """Return a function that calls increment(). Nothing is captured."""
    def counter():
        return increment()
    return counter                        # no closure over 'count' exists


def example_3():
    with dyn_frame(count=0):              # PUSH {'count': 0}
        my_counter = get_counter()
        print(my_counter())               # 1
        print(my_counter())               # 2
        print(dyn_get("count"))           # 2 -- same binding, mutated twice
        return my_counter                 # hand the function back OUT


def example_3b(my_counter):
    """The divergence: a "closure" that outlives the frame it depended on.

    Lexically (lexical.py) my_counter keeps working forever, because the cell
    holding count travels with the function object. Dynamically the binding
    lived on the stack, and that frame is gone.
    """
    print(f"  stack after example_3 returned: {stack_view()}")
    try:
        my_counter()
    except NameError as err:
        print(f"  my_counter() -> NameError: {err}")

    # ...and called from a DIFFERENT frame, it silently counts something else.
    with dyn_frame(count=100):
        print(f"  called inside a frame with count=100 -> {my_counter()}")


# ---------------------------------------------------------------------------
# EXAMPLE 4 - three shadowing binds. Still identical to lexical output.
# ---------------------------------------------------------------------------
def example_4():
    with dyn_frame(name="global"):
        def outer():
            with dyn_frame(name="outer"):
                def inner():
                    with dyn_frame(name="inner"):
                        # TRACE  top frame binds 'name' itself -> immediate hit,
                        #        nothing below is consulted.
                        print(f"Inner: {dyn_get('name')}")
                inner()
                print(f"Outer: {dyn_get('name')}")     # 'outer' frame restored
        outer()
        print(f"Global: {dyn_get('name')}")            # 'global' frame restored


# ---------------------------------------------------------------------------
# EXAMPLE 5 - THE DIVERGENCE. Same callee, two callers, two different answers.
# ---------------------------------------------------------------------------
def report():
    with dyn_frame():
        # TRACE  report() binds nothing and is nested inside nothing. Lexically
        #        that forced it to the module global every time. Dynamically it
        #        takes whatever its CALLER most recently bound, so its behavior
        #        is decided at the call site -- a different answer per caller.
        print(f"    report() sees status = {dyn_get('status')!r}")


def audit_run():
    with dyn_frame(status="auditing"):
        print("  audit_run  (binds status = 'auditing')")
        report()                          # -> 'auditing'   (was 'module-level')


def deploy_run():
    with dyn_frame(status="deploying"):
        print("  deploy_run (binds status = 'deploying')")
        report()                          # -> 'deploying'  (was 'module-level')


def example_5():
    with dyn_frame(status="module-level"):    # the simulated global frame
        audit_run()
        deploy_run()
        print(f"  outermost status is still {dyn_get('status')!r}")

    # With no frame at all, the same call cannot be resolved -- an error the
    # lexical version can never produce, because its answer was fixed at
    # compile time.
    print("  calling report() with an empty stack:")
    try:
        report()
    except NameError as err:
        print(f"    -> NameError: {err}")


# ---------------------------------------------------------------------------
def main():
    print("Example 1:")
    example_1()

    print("\nExample 2:")
    example_2()

    print("\nExample 3:")
    my_counter = example_3()

    print("\nExample 3b: (added) the counter after its frame is gone")
    example_3b(my_counter)

    print("\nExample 4:")
    example_4()

    print("\nExample 5: (added) definition site vs. call site")
    example_5()

    print("\n" + "=" * 68)
    print("SUMMARY OF DIVERGENCE")
    print("=" * 68)
    rows = [
        ("Ex 1  inner sees x",        "outer",        "outer",        "same"),
        ("Ex 2  inner sees x",        "20",           "20",           "same"),
        ("Ex 3  counter results",     "1, 2, 2",      "1, 2, 2",      "same"),
        ("Ex 3b counter after return", "3 (works)",   "NameError",    "DIFFERS"),
        ("Ex 4  inner sees name",     "inner",        "inner",        "same"),
        ("Ex 5  report() in audit",   "module-level", "auditing",     "DIFFERS"),
        ("Ex 5  report() in deploy",  "module-level", "deploying",    "DIFFERS"),
        ("Ex 5  report() bare call",  "module-level", "NameError",    "DIFFERS"),
    ]
    print(f"{'case':<28}{'lexical':<15}{'dynamic':<14}verdict")
    print("-" * 68)
    for case, lex, dyn, verdict in rows:
        print(f"{case:<28}{lex:<15}{dyn:<14}{verdict}")
    print("-" * 68)
    print("Examples 1-4 agree because each callee was written inside the same")
    print("function that called it -- the lexical chain and the call chain were")
    print("the same chain. The models split only once those chains differ.")
    print("=" * 68)


if __name__ == "__main__":
    main()
