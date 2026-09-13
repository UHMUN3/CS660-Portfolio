# Functional version — MODIFIED for Part Three
# Variation: the report now includes a letter-grade distribution (A–F), and the
# passing threshold is a parameter instead of a hardcoded 70.
# Lines tagged MODIFICATION mark every change from the original.

from functools import reduce, partial

calculate_count = len
calculate_sum = sum
calculate_average = lambda grades: sum(grades) / len(grades)
find_maximum = lambda grades: reduce(max, grades)
find_minimum = lambda grades: reduce(min, grades)

# MODIFICATION: the threshold is now an argument, so the predicate and both
# functions built on it all had to change signature — the parameter must be
# threaded through the entire call chain because pure functions share no state.
is_passing = lambda threshold, grade: grade >= threshold
# MODIFICATION: partial (imported but unused in the original) finally earns its
# import by binding the threshold onto the predicate for filter().
count_passing = lambda grades, threshold: len(list(filter(partial(is_passing, threshold), grades)))
calculate_pass_rate = lambda grades, threshold: (count_passing(grades, threshold) / len(grades)) * 100

# MODIFICATION: new pure function mapping a numeric grade to a letter.
def letter_for(grade):
    if grade >= 90:
        return "A"
    elif grade >= 80:
        return "B"
    elif grade >= 70:
        return "C"
    elif grade >= 60:
        return "D"
    return "F"

# MODIFICATION: new function — builds the distribution by mapping letter_for
# over the grades and reducing the letters into a dict without mutating it.
def grade_distribution(grades):
    letters = map(letter_for, grades)
    return reduce(lambda dist, letter: {**dist, letter: dist.get(letter, 0) + 1}, letters, {})

# MODIFICATION: new function — formats the distribution in a fixed A–F order.
def format_distribution(dist):
    return " ".join(f"{letter}={dist.get(letter, 0)}" for letter in "ABCDF")

# MODIFICATION: takes the threshold so the pass-rate lambda can receive it; the
# distribution line is simply one more element appended to the list.
def create_analysis_functions(passing_threshold):
    return [
        lambda grades: f"Total students: {calculate_count(grades)}",
        lambda grades: f"Average grade: {calculate_average(grades):.1f}",
        lambda grades: f"Highest grade: {find_maximum(grades)}",
        lambda grades: f"Lowest grade: {find_minimum(grades)}",
        lambda grades: f"Pass rate: {calculate_pass_rate(grades, passing_threshold):.1f}%",
        lambda grades: f"Grade distribution: {format_distribution(grade_distribution(grades))}"
    ]

# MODIFICATION: signature change ripples up one more level.
def generate_report(grades, passing_threshold=70):
    analysis_functions = create_analysis_functions(passing_threshold)
    return list(map(lambda func: func(grades), analysis_functions))

# MODIFICATION: takes the threshold only to display it in the header.
def print_report(report_lines, passing_threshold):
    print(f"Grade Analysis Results (passing threshold: {passing_threshold}):")
    list(map(print, report_lines))

def analyze_grades():
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]
    # MODIFICATION: run the report under both thresholds to demonstrate the change.
    for threshold in (70, 80):
        report = generate_report(grades, threshold)
        print_report(report, threshold)
        print()

if __name__ == "__main__":
    analyze_grades()
