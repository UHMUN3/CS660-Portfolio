# Imperative version — MODIFIED for Part Three
# Variation: the report now includes a letter-grade distribution (A–F), and the
# passing threshold is a parameter instead of a hardcoded 70.
# Lines tagged MODIFICATION mark every change from the original.

# MODIFICATION: the threshold is now a parameter, which required changing the
# function signature — every piece of state this function uses lives inside it.
def analyze_grades(passing_threshold=70):
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]

    total = 0
    count = 0
    highest = grades[0]
    lowest = grades[0]
    passing_count = 0
    # MODIFICATION: five new accumulators join the loop's shared mutable state.
    a_count = 0
    b_count = 0
    c_count = 0
    d_count = 0
    f_count = 0

    for grade in grades:
        total += grade
        count += 1

        if grade > highest:
            highest = grade

        if grade < lowest:
            lowest = grade

        # MODIFICATION: comparison now uses the parameter instead of a literal 70.
        if grade >= passing_threshold:
            passing_count += 1

        # MODIFICATION: new branch chain inserted into the existing loop body.
        if grade >= 90:
            a_count += 1
        elif grade >= 80:
            b_count += 1
        elif grade >= 70:
            c_count += 1
        elif grade >= 60:
            d_count += 1
        else:
            f_count += 1

    average = total / count
    pass_rate = (passing_count / count) * 100

    print(f"Grade Analysis Results (passing threshold: {passing_threshold}):")
    print(f"Total students: {count}")
    print(f"Average grade: {average:.1f}")
    print(f"Highest grade: {highest}")
    print(f"Lowest grade: {lowest}")
    print(f"Pass rate: {pass_rate:.1f}%")
    # MODIFICATION: new output line for the distribution.
    print(f"Grade distribution: A={a_count} B={b_count} C={c_count} D={d_count} F={f_count}")

if __name__ == "__main__":
    analyze_grades()
    print()
    # MODIFICATION: because computation and printing are fused, demonstrating a
    # different threshold means re-running the entire report.
    analyze_grades(passing_threshold=80)
