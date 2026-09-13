"""
CS 660 - Module Three Activity
Part Two, Steps 7 and 9: Lexical Scoping in Nested Functions

Examples 1-4 are the provided starter code, unchanged in behavior. In-line
comments have been added to trace how each name is resolved. Example 5 is an
addition that isolates the one case where lexical and dynamic scoping actually
disagree, so the two models can be compared directly (see dynamic.py).

HOW PYTHON RESOLVES A NAME -- the LEGB rule
    L  Local      names assigned inside the running function
    E  Enclosing  locals of any function this one is textually nested inside
    G  Global     module-level names
    B  Built-in   print, len, ...

The decisive point: the E step walks the chain of functions this one is WRITTEN
inside. That chain is fixed when the source is compiled and does not depend on
who called the function. This is lexical (static) scoping.

RUN
    python3 lexical.py
"""


def example_1():
    """One level of nesting: the closure reads the enclosing local."""
    x = "outer"                       # BIND  example_1.x = "outer"

    def inner():
        # TRACE  'x' is not assigned in inner -> not Local.
        #        Step out one lexical level to example_1 -> Enclosing hit.
        #        Resolves to "outer".
        print(f"Inner sees: {x}")

    inner()                           # prints: Inner sees: outer
    print(f"Outer has: {x}")          # prints: Outer has: outer
    # inner() only READ x, so example_1.x is untouched.


def example_2():
    """Two levels: the nearest enclosing binding wins, not the outermost."""
    x = 10                            # BIND  example_2.x = 10

    def middle():
        x = 20                        # BIND  middle.x = 20 -- a NEW name that
                                      # shadows example_2.x; it does not
                                      # reassign it (no nonlocal declared).

        def inner():
            # TRACE  'x' not Local to inner.
            #        Enclosing chain is inner -> middle -> example_2.
            #        First hit is middle.x = 20, so the search STOPS there.
            #        example_2.x = 10 is never reached.
            print(f"Inner sees: {x}")

        inner()                       # prints: Inner sees: 20
        print(f"Middle has: {x}")     # prints: Middle has: 20   (middle.x)

    middle()
    print(f"Outer has: {x}")          # prints: Outer has: 10    (example_2.x,
                                      # proving the shadowing was local only)


def example_3():
    """A closure that WRITES to an enclosing binding, via nonlocal."""
    count = 0                         # BIND  example_3.count = 0

    def increment():
        nonlocal count                # DECLARE: 'count' is not local here.
                                      # Rebind the Enclosing example_3.count.
                                      # Without this line, `count += 1` would
                                      # read-then-write a Local and raise
                                      # UnboundLocalError.
        count += 1                    # MUTATE example_3.count in place
        return count

    def get_counter():
        def counter():
            # TRACE  'increment' is not Local to counter; it is found in the
            #        Enclosing scope example_3. The returned function keeps
            #        that link alive after get_counter() has already returned.
            return increment()
        return counter

    my_counter = get_counter()        # closure escapes its defining call
    print(my_counter())               # prints: 1   (count 0 -> 1)
    print(my_counter())               # prints: 2   (count 1 -> 2)
    print(count)                      # prints: 2   -- same binding, not a copy
    return my_counter                 # hand the closure back OUT (see 3b)


def example_3b(my_counter):
    """ADDED (Step 10): the closure still works after example_3 has returned.

    example_3's frame is gone from the call stack, but the cell holding `count`
    is kept alive by the function object itself. Lexical scope is a property of
    the code, so it does not expire when a call does. dynamic.py, example_3b,
    runs the identical call and raises NameError instead.
    """
    print("  example_3 has already returned; calling my_counter() anyway:")
    print(f"  -> {my_counter()}")      # prints: 3   (count 2 -> 3)


def example_4():
    """Three sibling bindings of one name; each frame sees its own."""
    name = "global"                   # BIND  example_4.name = "global"
                                      # NOTE: despite the string, this is a
                                      # LOCAL of example_4, not a module global.

    def outer():
        name = "outer"                # BIND  outer.name -- shadows example_4

        def inner():
            name = "inner"            # BIND  inner.name -- shadows outer
            # TRACE  'name' IS assigned in inner, so the Local step succeeds
            #        immediately and no enclosing scope is consulted.
            print(f"Inner: {name}")   # prints: Inner: inner

        inner()
        print(f"Outer: {name}")       # prints: Outer: outer   (unchanged)

    outer()
    print(f"Global: {name}")          # prints: Global: global (unchanged)
    # Three distinct bindings coexisted. Assignment never leaked outward.


# ---------------------------------------------------------------------------
# ADDED FOR COMPARISON (Step 10)
#
# Examples 1-4 all call functions from inside the same functions they are
# written in, so the lexical chain and the call chain happen to match. When
# they match, lexical and dynamic scoping produce identical output and the
# distinction is invisible. Example 5 separates them: report() is DEFINED at
# module level but CALLED from two functions that each bind `status`
# themselves. This is where the two models diverge.
# ---------------------------------------------------------------------------

status = "module-level"               # BIND  the real module Global


def report():
    # TRACE (LEXICAL)  'status' not Local to report.
    #                  report is nested inside nothing, so there is no
    #                  Enclosing scope to search -> go straight to Global.
    #                  Resolves to "module-level" on EVERY call, no matter
    #                  who the caller is or what the caller named its own
    #                  variables. The answer is fixed by where report() is
    #                  WRITTEN.
    print(f"    report() sees status = {status!r}")


def audit_run():
    status = "auditing"               # BIND  audit_run.status -- a local.
    # This binding is invisible to report(). report() is not written inside
    # audit_run, so audit_run's frame is not on report's lexical chain.
    print("  audit_run  (its own local status = 'auditing')")
    report()                          # prints: module-level


def deploy_run():
    status = "deploying"              # BIND  deploy_run.status -- also local
    print("  deploy_run (its own local status = 'deploying')")
    report()                          # prints: module-level


def example_5():
    """Same callee, two different callers, one unchanging answer."""
    audit_run()
    deploy_run()
    print(f"  module-level status is still {status!r}")


if __name__ == "__main__":
    print("Example 1:")
    example_1()

    print("\nExample 2:")
    example_2()

    print("\nExample 3:")
    my_counter = example_3()

    print("\nExample 3b: (added) the closure after its defining call returned")
    example_3b(my_counter)

    print("\nExample 4:")
    example_4()

    print("\nExample 5: (added) definition site vs. call site")
    example_5()
