# Imperative version — annotated for Part Two (Readability Assessment)
# Annotation key: [STRENGTH] = readability strength, [WEAKNESS] = readability weakness

def analyze_grades():
    # [WEAKNESS] Input data is hardcoded inside the function, so the data and the
    # algorithm cannot be read (or reused) independently of each other.
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]

    # [STRENGTH] Descriptive accumulator names (total, count, highest, lowest,
    # passing_count) make the purpose of each variable obvious at a glance.
    total = 0
    count = 0
    # [STRENGTH] Seeding highest/lowest from grades[0] is a common, recognizable idiom.
    # [WEAKNESS] ...but it raises IndexError on an empty list, and nothing in the
    # code warns the reader about that assumption.
    highest = grades[0]
    lowest = grades[0]
    passing_count = 0

    # [STRENGTH] A single explicit loop: execution can be traced line by line,
    # top to bottom, with no hidden control flow.
    for grade in grades:
        total += grade
        # [WEAKNESS] Manually counting (count += 1) duplicates what len(grades)
        # already provides — one more piece of mutable state to track while reading.
        count += 1

        if grade > highest:
            highest = grade

        if grade < lowest:
            lowest = grade

        # [WEAKNESS] The passing threshold 70 is a magic number: it has no name,
        # no explanation, and a reader cannot tell if it is policy or coincidence.
        if grade >= 70:
            passing_count += 1

    # [STRENGTH] Derived values are computed right after the loop, close to where
    # they are used, so the reader never has to jump around the file.
    average = total / count
    pass_rate = (passing_count / count) * 100

    # [WEAKNESS] Computation and presentation are fused in one function — the
    # statistics cannot be reused, tested, or read separately from the printing.
    print("Grade Analysis Results:")
    print(f"Total students: {count}")
    # [STRENGTH] f-strings with :.1f formatting keep the output code compact and readable.
    print(f"Average grade: {average:.1f}")
    print(f"Highest grade: {highest}")
    print(f"Lowest grade: {lowest}")
    print(f"Pass rate: {pass_rate:.1f}%")

if __name__ == "__main__":
    analyze_grades()
