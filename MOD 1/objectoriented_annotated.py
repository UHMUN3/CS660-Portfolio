# Object-oriented version — annotated for Part Two (Readability Assessment)
# Annotation key: [STRENGTH] = readability strength, [WEAKNESS] = readability weakness

# [STRENGTH] The class name states exactly what the object is for, and the
# method names together read like a table of contents for the whole file.
class GradeAnalyzer:
    # [STRENGTH] The grade list is stored once at construction — a single source
    # of truth that every method draws from, with no parameter passing to follow.
    # [WEAKNESS] No docstrings anywhere: the class and its methods rely entirely
    # on naming, and expectations (e.g., non-empty list) are never stated.
    def __init__(self, grades):
        self.grades = grades

    # [WEAKNESS] Java-style get_ prefixes are unidiomatic in Python — properties
    # (analyzer.count) would read more naturally than analyzer.get_count().
    def get_count(self):
        return len(self.grades)

    # [STRENGTH] Each statistic lives in its own short method built on a familiar
    # built-in (len, sum, max, min) — every method body is one obvious line.
    def get_average(self):
        return sum(self.grades) / len(self.grades)

    def get_highest(self):
        return max(self.grades)

    def get_lowest(self):
        return min(self.grades)

    def get_pass_rate(self):
        # [STRENGTH] The generator expression is an idiomatic, compact way to
        # count matches without building an intermediate list.
        # [WEAKNESS] The passing threshold 70 is a magic number buried inside a
        # method body — nothing names it or marks it as changeable policy.
        passing_count = sum(1 for grade in self.grades if grade >= 70)
        return (passing_count / len(self.grades)) * 100

    # [WEAKNESS] print_results mixes presentation into an otherwise purely
    # computational class — the class now has two reasons to change.
    def print_results(self):
        print("Grade Analysis Results:")
        # [STRENGTH] Output lines call the public methods by name, so the report
        # doubles as documentation of the class's interface.
        print(f"Total students: {self.get_count()}")
        print(f"Average grade: {self.get_average():.1f}")
        print(f"Highest grade: {self.get_highest()}")
        print(f"Lowest grade: {self.get_lowest()}")
        print(f"Pass rate: {self.get_pass_rate():.1f}%")

# [WEAKNESS] For a task this small, the class adds ceremony (class, __init__,
# self) that a reader must step through before reaching any actual logic.
def analyze_grades():
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]
    analyzer = GradeAnalyzer(grades)
    analyzer.print_results()

if __name__ == "__main__":
    analyze_grades()
