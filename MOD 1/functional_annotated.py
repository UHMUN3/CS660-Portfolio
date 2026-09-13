# Functional version — annotated for Part Two (Readability Assessment)
# Annotation key: [STRENGTH] = readability strength, [WEAKNESS] = readability weakness

# [WEAKNESS] partial is imported but never used anywhere in this file — dead
# imports make the reader hunt for a usage that does not exist.
from functools import reduce, partial

# [WEAKNESS] Aliasing built-ins (calculate_count = len) forces the reader to
# chase the alias back to its definition just to learn it is plain len().
calculate_count = len
calculate_sum = sum
# [WEAKNESS] Assigning lambdas to names (discouraged by PEP 8) loses docstrings
# and produces unhelpful tracebacks compared to a normal def statement.
calculate_average = lambda grades: sum(grades) / len(grades)
# [WEAKNESS] reduce(max, grades) obscures the far simpler max(grades) — paradigm
# purity is chosen over the idiom every Python reader already knows.
find_maximum = lambda grades: reduce(max, grades)
find_minimum = lambda grades: reduce(min, grades)

# [STRENGTH] The passing threshold is wrapped in a named predicate (is_passing),
# so the rule "70 or above passes" is documented by the function name itself.
is_passing = lambda grade: grade >= 70
# [WEAKNESS] filter -> list -> len is a three-step conversion chain just to
# count matches; a generator expression with sum() would read more directly.
count_passing = lambda grades: len(list(filter(is_passing, grades)))
# [STRENGTH] Each statistic is a small, named, single-purpose function — the
# name documents the intent, and each piece can be read (and tested) alone.
calculate_pass_rate = lambda grades: (count_passing(grades) / len(grades)) * 100

def create_analysis_functions():
    # [WEAKNESS] Returning a list of lambdas is heavy indirection: to know what
    # the report will say, the reader must mentally execute map() over functions
    # instead of just reading print statements in order.
    return [
        lambda grades: f"Total students: {calculate_count(grades)}",
        lambda grades: f"Average grade: {calculate_average(grades):.1f}",
        lambda grades: f"Highest grade: {find_maximum(grades)}",
        lambda grades: f"Lowest grade: {find_minimum(grades)}",
        lambda grades: f"Pass rate: {calculate_pass_rate(grades):.1f}%"
    ]

# [STRENGTH] Pure computation (generate_report) is cleanly separated from I/O
# (print_report) — every function above this line has no side effects at all.
def generate_report(grades):
    analysis_functions = create_analysis_functions()
    return list(map(lambda func: func(grades), analysis_functions))

def print_report(report_lines):
    print("Grade Analysis Results:")
    # [WEAKNESS] list(map(print, ...)) abuses map for side effects and builds a
    # throwaway list of None values — a plain for loop states the intent honestly.
    list(map(print, report_lines))

def analyze_grades():
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]
    report = generate_report(grades)
    print_report(report)

if __name__ == "__main__":
    analyze_grades()
