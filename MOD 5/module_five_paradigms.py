"""
CS 660 Module Five Activity - Paradigm Comparison
Author: Aaron Foster
Date: Aug 9th 2026

Problem: Given a list of integers, filter out all even numbers, square the
remaining odd numbers, and return the result as a new list.

The same algorithm is solved three times below - imperatively, with objects,
and functionally - so the three approaches can be compared directly.
"""

from abc import ABC, abstractmethod
from functools import reduce


# ---------------------------------------------------------------------------
# 1. IMPERATIVE APPROACH
# ---------------------------------------------------------------------------

def square_odds_imperative(numbers):
    """Filter evens and square odds using explicit, step-by-step statements."""

    # IMPERATIVE PRINCIPLE - explicit state: the algorithm is defined by a
    # variable the program owns and repeatedly modifies. `result` starts empty
    # and is the accumulated state of the computation so far.
    result = []

    # IMPERATIVE PRINCIPLE - explicit control flow: the programmer, not the
    # language, dictates the order of execution. This loop states *how* to walk
    # the list, one index at a time, rather than describing *what* is wanted.
    for number in numbers:

        # IMPERATIVE PRINCIPLE - conditional branching: the decision to keep or
        # discard a value is a statement executed at a specific moment in time.
        if number % 2 != 0:

            # IMPERATIVE PRINCIPLE - mutation: `append` changes `result` in
            # place. The same variable holds different values at different
            # points in the program, so the answer depends on execution order.
            result.append(number ** 2)

    # The final value of the mutated state is the answer.
    return result


# ---------------------------------------------------------------------------
# 2. OBJECT-ORIENTED APPROACH
# ---------------------------------------------------------------------------

class NumberTransformer(ABC):
    """Abstract base class defining *what* a transformer does, not *how*."""

    # OO PRINCIPLE - encapsulation: the data being processed is bound together
    # with the behavior that processes it inside a single object. Callers
    # interact with the object's interface, not with a loose list.
    def __init__(self, numbers):
        # The leading underscore signals internal state. A defensive copy keeps
        # the caller's list from being mutated by anything this object does,
        # which protects the object's invariants.
        self._numbers = list(numbers)

    # OO PRINCIPLE - abstraction: subclasses must supply these two decisions,
    # but the algorithm below is written without knowing what they will be.
    @abstractmethod
    def should_keep(self, number):
        """Return True if `number` belongs in the result."""

    @abstractmethod
    def transform(self, number):
        """Return the value that `number` contributes to the result."""

    # OO PRINCIPLE - polymorphism: `process` calls `should_keep` and
    # `transform` without knowing which subclass supplies them. Swapping in a
    # different subclass changes the behavior of this method without editing
    # a single line of it.
    def process(self):
        return [self.transform(n) for n in self._numbers if self.should_keep(n)]


class OddSquarer(NumberTransformer):
    """Concrete transformer: keep odd numbers, square them."""

    # OO PRINCIPLE - inheritance: this class reuses `__init__` and `process`
    # from the parent and overrides only the two decisions that make it
    # specific to this problem.
    def should_keep(self, number):
        # The "filter out evens" rule now lives in a named, testable method
        # instead of being buried inside a loop condition.
        return number % 2 != 0

    def transform(self, number):
        # The "square it" rule is likewise isolated as its own responsibility.
        return number ** 2


def square_odds_object_oriented(numbers):
    """Convenience wrapper so all three approaches share one call signature."""
    # Message passing: build the object, then ask it to do the work.
    return OddSquarer(numbers).process()


# ---------------------------------------------------------------------------
# 3. FUNCTIONAL APPROACH
# ---------------------------------------------------------------------------

# FUNCTIONAL PRINCIPLE - pure functions: `is_odd` and `square` depend only on
# their arguments and have no side effects. Given the same input they always
# return the same output, which makes them safe to reuse, test, and compose.
def is_odd(number):
    return number % 2 != 0


def square(number):
    return number ** 2


def square_odds_functional(numbers):
    """Describe *what* the result is by composing functions over the input."""

    # FUNCTIONAL PRINCIPLE - higher-order functions: `filter` and `map` take
    # other functions as arguments. The predicate and the transformation are
    # passed in as values rather than written as inline statements.
    #
    # FUNCTIONAL PRINCIPLE - declarative composition: the output of `filter`
    # flows directly into `map`. There is no loop counter, no accumulator, and
    # no intermediate variable that changes value.
    #
    # FUNCTIONAL PRINCIPLE - immutability: nothing here modifies `numbers`.
    # `list()` materializes a brand-new list from the lazy pipeline, so the
    # caller's data is untouched.
    return list(map(square, filter(is_odd, numbers)))


def square_odds_functional_reduce(numbers):
    """Same result expressed as a fold, for comparison."""

    # FUNCTIONAL PRINCIPLE - recursion/folding over iteration: `reduce` walks
    # the list by repeatedly applying a function to an accumulated value. The
    # `acc + [square(n)]` expression builds a *new* list each step instead of
    # mutating one, which is the functional counterpart to `.append()`.
    return reduce(
        lambda acc, n: acc + [square(n)] if is_odd(n) else acc,
        numbers,
        [],
    )


# ---------------------------------------------------------------------------
# DEMONSTRATION
# ---------------------------------------------------------------------------

def main():
    sample = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    print("CS 660 Module Five Activity - Paradigm Comparison")
    print("=" * 52)
    print(f"Input list: {sample}\n")

    imperative = square_odds_imperative(sample)
    object_oriented = square_odds_object_oriented(sample)
    functional = square_odds_functional(sample)
    functional_fold = square_odds_functional_reduce(sample)

    print(f"1. Imperative result:       {imperative}")
    print(f"2. Object-oriented result:  {object_oriented}")
    print(f"3. Functional result:       {functional}")
    print(f"   Functional (reduce):     {functional_fold}\n")

    # All three paradigms solve the same problem, so all three must agree.
    all_match = imperative == object_oriented == functional == functional_fold
    print(f"All paradigms produce identical output: {all_match}")

    # The original list was never mutated by any approach.
    print(f"Original list unchanged:                {sample == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}\n")

    # Additional test cases confirm the logic holds at the edges.
    print("Additional test cases")
    print("-" * 52)
    for case in ([], [2, 4, 6], [1, 3, 5], [-3, -2, 0, 7]):
        print(f"  {str(case):<18} -> {square_odds_functional(case)}")


if __name__ == "__main__":
    main()
