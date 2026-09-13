# Object-oriented version — MODIFIED for Part Three
# Variation: the report now includes a letter-grade distribution (A–F), and the
# passing threshold is configurable instead of a hardcoded 70.
# Lines tagged MODIFICATION mark every change from the original.

class GradeAnalyzer:
    # MODIFICATION: the threshold becomes constructor state with a default —
    # one change in one place, and no other method signature had to move.
    def __init__(self, grades, passing_threshold=70):
        self.grades = grades
        self.passing_threshold = passing_threshold

    def get_count(self):
        return len(self.grades)

    def get_average(self):
        return sum(self.grades) / len(self.grades)

    def get_highest(self):
        return max(self.grades)

    def get_lowest(self):
        return min(self.grades)

    def get_pass_rate(self):
        # MODIFICATION: comparison now reads the instance attribute instead of 70.
        passing_count = sum(1 for grade in self.grades if grade >= self.passing_threshold)
        return (passing_count / len(self.grades)) * 100

    # MODIFICATION: new helper — maps one grade to its letter.
    def _letter_for(self, grade):
        if grade >= 90:
            return "A"
        if grade >= 80:
            return "B"
        if grade >= 70:
            return "C"
        if grade >= 60:
            return "D"
        return "F"

    # MODIFICATION: new method — the distribution was added without touching
    # any existing computation method.
    def get_distribution(self):
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for grade in self.grades:
            distribution[self._letter_for(grade)] += 1
        return distribution

    def print_results(self):
        # MODIFICATION: header now reports which threshold this instance uses.
        print(f"Grade Analysis Results (passing threshold: {self.passing_threshold}):")
        print(f"Total students: {self.get_count()}")
        print(f"Average grade: {self.get_average():.1f}")
        print(f"Highest grade: {self.get_highest()}")
        print(f"Lowest grade: {self.get_lowest()}")
        print(f"Pass rate: {self.get_pass_rate():.1f}%")
        # MODIFICATION: new output line for the distribution.
        distribution = self.get_distribution()
        dist_text = " ".join(f"{letter}={distribution[letter]}" for letter in "ABCDF")
        print(f"Grade distribution: {dist_text}")

def analyze_grades():
    grades = [85, 92, 78, 96, 88, 73, 91, 87, 94, 82]
    analyzer = GradeAnalyzer(grades)
    analyzer.print_results()
    print()
    # MODIFICATION: a second instance demonstrates per-object configuration —
    # two policies coexist without either interfering with the other.
    strict = GradeAnalyzer(grades, passing_threshold=80)
    strict.print_results()

if __name__ == "__main__":
    analyze_grades()
