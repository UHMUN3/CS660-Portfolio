"""CS 660 Module Four Activity - Recursion, Functional Constructs, and Exception Handling.

Author: Aaron Foster
Date:   Aug 2, 2026

Data set
--------
catalog.json - "Deep Space Survey 2025", a deeply nested astronomical catalog
containing galaxies -> star systems -> planets -> moons, plus nebulae, star
clusters, black holes, exoplanet systems, and pulsars. The structure is
irregular on purpose: some branches end in empty lists ("moons": []) and some
end in null ("binary_system": null), which makes it a realistic test for both
recursion and error handling.

Rubric map
----------
Part One: Recursion With Exception Handling
    1. Invalid inputs .............. total_mass_solar()
    2. Nested/structured data ...... find_object_by_id()
    3. Innermost leaf data ......... collect_leaves()

Part Two: Functional Constructs
    4. Anonymous function .......... report_planets(), report_leaf_rounding()
    5. Higher-order function ....... report_planets(), summarize_by()
    6. Function as an argument ..... apply_to_leaves(), summarize_by()

"""

import json
from functools import reduce
from pathlib import Path

# A cycle in the data (or a self-referencing dict built by hand) would otherwise
# recurse until Python's own stack limit blows up with an unhelpful traceback.
# Guarding explicitly lets every recursive function fail with a clear message.
MAX_DEPTH = 50

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class CatalogError(Exception):
    """Base class for every error raised while loading or walking the catalog."""


class InvalidNodeError(CatalogError):
    """Raised when an argument cannot be treated as catalog data."""


class CatalogDepthError(CatalogError):
    """Raised when recursion passes MAX_DEPTH, which signals cyclic data."""


def load_catalog(path=CATALOG_PATH):
    """Read and parse catalog.json, converting low-level errors into CatalogError.

    The caller should not have to know whether the failure was a missing file or
    malformed JSON, so both are re-raised as one exception type it can handle.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise CatalogError(f"Catalog file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Catalog file is not valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Part One, Criterion 1: exception handling for invalid inputs in recursion
# ---------------------------------------------------------------------------

def total_mass_solar(node, field="mass_solar_masses", depth=0):
    """Recursively add up every `field` value found anywhere in the catalog.

    Two different kinds of invalid input are handled here:

    * Invalid arguments. A caller who passes a scalar instead of a catalog, or
      an empty field name, gets an InvalidNodeError instead of a silent 0.0.
      Cyclic data is caught by the depth guard.
    * Invalid data. A mass stored as "unknown", None, or a list cannot be added
      to a running total. Crashing the traversal would throw away the other 24
      objects, so the bad value is caught, reported, and skipped.

    Base case: a scalar (or an empty container) has nothing to add and returns
    0.0. Every recursive call receives a strictly smaller sub-structure and a
    larger `depth`, so the recursion always terminates.
    """
    if depth == 0:
        # Validate the caller's arguments once, at the top of the recursion,
        # rather than re-checking them on every one of the hundreds of calls.
        if not isinstance(field, str) or not field:
            raise InvalidNodeError(f"field must be a non-empty string, got {field!r}")
        if not isinstance(node, (dict, list)):
            raise InvalidNodeError(
                f"expected a dict or list to search, got {type(node).__name__}"
            )

    if depth > MAX_DEPTH:
        raise CatalogDepthError(f"exceeded max depth of {MAX_DEPTH}; data may be cyclic")

    total = 0.0

    if isinstance(node, dict):
        for key, value in node.items():
            if key == field:
                try:
                    total += float(value)
                except (TypeError, ValueError):
                    # float() raises TypeError for None/list/dict and ValueError
                    # for a non-numeric string. Both mean "unusable mass".
                    print(f"    [warn] skipping non-numeric {field}: {value!r}")
            else:
                total += total_mass_solar(value, field, depth + 1)
    elif isinstance(node, list):
        for item in node:
            total += total_mass_solar(item, field, depth + 1)

    return total


# ---------------------------------------------------------------------------
# Part One, Criterion 2: exception handling in recursion over nested data
# ---------------------------------------------------------------------------

def find_object_by_id(node, target_id, path="catalog", depth=0):
    """Recursively search the nested catalog for the object whose *_id matches.

    Returns a (path, object) tuple for the first match, or None if the id is not
    present anywhere in the tree.

    This data set is not uniformly shaped: "surrounding_disk" and
    "binary_system" are null on some records, "moons" and "forming_stars" are
    sometimes empty, and a hand-built or partially converted catalog can contain
    a dict whose keys are not strings. Descending into those branches raises
    AttributeError or TypeError. Catching it per branch means one malformed
    record does not abort the search of the other five object categories.
    """
    if depth > MAX_DEPTH:
        raise CatalogDepthError(f"exceeded max depth of {MAX_DEPTH}; data may be cyclic")

    try:
        if isinstance(node, dict):
            # Check this object itself before descending, so the shallowest
            # match wins and the returned path stays as short as possible.
            for key, value in node.items():
                if key.endswith("_id") and value == target_id:
                    return (path, node)

            for key, value in node.items():
                found = find_object_by_id(value, target_id, f"{path}.{key}", depth + 1)
                if found is not None:
                    return found

        elif isinstance(node, list):
            for index, item in enumerate(node):
                found = find_object_by_id(item, target_id, f"{path}[{index}]", depth + 1)
                if found is not None:
                    return found

    except (AttributeError, TypeError) as exc:
        # AttributeError: a key is not a string, so .endswith() does not exist.
        # TypeError: a value claims to be a container but is not iterable.
        print(f"    [warn] skipping malformed branch at {path}: {exc}")
        return None

    # Base case: a scalar, an empty container, or an exhausted branch.
    return None


# ---------------------------------------------------------------------------
# Part One, Criterion 3: recursive walk to the innermost leaf data
# ---------------------------------------------------------------------------

def collect_leaves(node, path="catalog", depth=0):
    """Recursively walk the structure and return every innermost leaf.

    A leaf is a value with no further structure beneath it: a string, number,
    boolean, or null. Empty containers count as leaves too, so a planet with
    "moons": [] still appears in the output instead of vanishing.

    Each leaf is returned as a (path, value) pair, where the path records the
    chain of keys and list indices that reach it, for example
    catalog.astronomical_catalog.galaxies[0].star_systems[0].planets[0].moons[0].name

    Base case: node is not a dict or list, so it is itself the leaf.
    Recursive case: descend into each child with a longer path and a larger
    depth, guaranteeing progress toward the base case.
    """
    if depth > MAX_DEPTH:
        raise CatalogDepthError(f"exceeded max depth of {MAX_DEPTH}; data may be cyclic")

    if isinstance(node, dict) and node:
        leaves = []
        for key, value in node.items():
            leaves.extend(collect_leaves(value, f"{path}.{key}", depth + 1))
        return leaves

    if isinstance(node, list) and node:
        leaves = []
        for index, item in enumerate(node):
            leaves.extend(collect_leaves(item, f"{path}[{index}]", depth + 1))
        return leaves

    return [(path, node)]


def collect_dicts_with(node, required_key, depth=0):
    """Recursively gather every dict that contains `required_key`.

    Used to flatten the tree into flat record lists for Part Two. Asking for
    "planet_id" collects planets from both the galaxy branch and the
    exoplanet_systems branch, even though they sit at different depths.
    """
    if depth > MAX_DEPTH:
        raise CatalogDepthError(f"exceeded max depth of {MAX_DEPTH}; data may be cyclic")

    found = []

    if isinstance(node, dict):
        if required_key in node:
            found.append(node)
        for value in node.values():
            found.extend(collect_dicts_with(value, required_key, depth + 1))
    elif isinstance(node, list):
        for item in node:
            found.extend(collect_dicts_with(item, required_key, depth + 1))

    return found


# ---------------------------------------------------------------------------
# Part Two, Criterion 6: functions that accept another function as an argument
# ---------------------------------------------------------------------------

def apply_to_leaves(node, func, depth=0):
    """Return a copy of the structure with `func` applied to every leaf value.

    `func` is supplied by the caller, so this one recursive walk can round every
    float, redact every string, or convert every unit without being rewritten.
    The original structure is never mutated; a new one is built on the way back
    up the recursion.
    """
    if depth > MAX_DEPTH:
        raise CatalogDepthError(f"exceeded max depth of {MAX_DEPTH}; data may be cyclic")

    if isinstance(node, dict):
        return {key: apply_to_leaves(value, func, depth + 1) for key, value in node.items()}

    if isinstance(node, list):
        return [apply_to_leaves(item, func, depth + 1) for item in node]

    try:
        return func(node)
    except (TypeError, ValueError) as exc:
        # The caller's function may not accept every leaf type in the catalog.
        # Leaving the original value in place is safer than losing the record.
        print(f"    [warn] leaf {node!r} left unchanged: {exc}")
        return node


def summarize_by(records, key_func, value_func, combine):
    """Group `records` and reduce each group to a single value.

    All three parameters are functions, which is what makes this higher order:
        key_func(record)   -> the group a record belongs to
        value_func(record) -> the number that record contributes
        combine(a, b)      -> how two contributions merge (sum, max, and so on)
    """
    groups = {}
    for record in records:
        key = key_func(record)
        groups.setdefault(key, []).append(value_func(record))
    return {key: reduce(combine, values) for key, values in groups.items()}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def banner(text):
    print(f"\n{text}\n{'-' * len(text)}")


def report_invalid_inputs(catalog):
    """Criterion 1."""
    banner("Criterion 1: exception handling for invalid inputs in recursion")

    total = total_mass_solar(catalog)
    print(f"  Total catalogued mass: {total:,.2f} solar masses")

    # Corrupt a copy so the in-recursion data handler can be seen firing.
    corrupted = json.loads(json.dumps(catalog))
    corrupted["astronomical_catalog"]["galaxies"][0]["mass_solar_masses"] = "unknown"
    corrupted["astronomical_catalog"]["black_holes"][0]["mass_solar_masses"] = None
    print("  Re-running against a copy with two corrupted mass values:")
    salvaged = total_mass_solar(corrupted)
    print(f"  Salvaged total: {salvaged:,.2f} solar masses "
          f"({total - salvaged:,.2f} lost to bad records)")

    # Bad arguments are the caller's mistake, so they are raised, not swallowed.
    for bad_argument in (42, "catalog.json"):
        try:
            total_mass_solar(bad_argument)
        except InvalidNodeError as exc:
            print(f"  Rejected {bad_argument!r}: {exc}")

    # The depth guard turns runaway recursion into a readable error.
    cyclic = {"name": "loop"}
    cyclic["self"] = cyclic
    try:
        total_mass_solar(cyclic)
    except CatalogDepthError as exc:
        print(f"  Caught cyclic data: {exc}")


def report_nested_search(catalog):
    """Criterion 2."""
    banner("Criterion 2: exception handling while recursing nested data")

    for target in ("MON-003", "TRP-003", "PSR-002", "NOPE-999"):
        result = find_object_by_id(catalog, target)
        if result is None:
            print(f"  {target}: not found in catalog")
        else:
            path, obj = result
            print(f"  {target}: {obj.get('name')}")
            print(f"      at {path}")

    # A dict with a non-string key cannot come from JSON, but can easily arrive
    # from a database row or a hand-built fixture. The search should degrade
    # instead of dying, so it still finds the good record that follows.
    malformed = {
        "broken_branch": {1: "an integer key breaks key.endswith()"},
        "good_branch": {"probe_id": "PRB-001", "name": "Voyager Probe"},
    }
    print("  Searching a structure with a malformed branch:")
    result = find_object_by_id(malformed, "PRB-001")
    print(f"  Recovered and still found: {result[1]['name']}")


def report_leaves(catalog):
    """Criterion 3."""
    banner("Criterion 3: recursive walk to the innermost leaf data")

    leaves = collect_leaves(catalog)
    print(f"  Innermost leaves found: {len(leaves)}")

    deepest_path, deepest_value = max(leaves, key=lambda leaf: leaf[0].count("."))
    print(f"  Deepest leaf: {deepest_value!r}")
    print(f"      at {deepest_path}")

    print("  First five leaves:")
    for path, value in leaves[:5]:
        print(f"      {path} = {value!r}")

    print("  Leaves beneath the first moon in the catalog:")
    moon_leaves = [leaf for leaf in leaves if ".moons[0]." in leaf[0]]
    for path, value in moon_leaves[:6]:
        print(f"      {path.split('.moons[0].')[-1]:<22} = {value!r}")


def report_planets(catalog):
    """Criteria 4 and 5."""
    banner("Criteria 4 and 5: anonymous and higher-order functions")

    planets = collect_dicts_with(catalog, "planet_id")
    print(f"  Planets collected across every branch: {len(planets)}")

    # Anonymous functions passed to the built-in higher-order functions
    # sorted(), filter(), map(), and functools.reduce().
    by_period = sorted(planets, key=lambda p: p["orbital_period_days"])
    print(f"  Shortest year: {by_period[0]['name']} "
          f"({by_period[0]['orbital_period_days']} days)")
    print(f"  Longest year:  {by_period[-1]['name']} "
          f"({by_period[-1]['orbital_period_days']} days)")

    habitable = list(filter(lambda p: p.get("habitable_zone") is True, planets))
    names = list(map(lambda p: p["name"], habitable))
    print(f"  In the habitable zone: {', '.join(names)}")

    total_earth_masses = reduce(
        lambda running, p: running + p["mass_earth_masses"], planets, 0.0
    )
    print(f"  Combined planetary mass: {total_earth_masses:,.2f} Earth masses")

    describe = lambda p: f"{p['name']:<22} {p['mass_earth_masses']:>8.2f} Earth masses"
    print("  Three most massive planets:")
    heaviest = sorted(planets, key=lambda p: -p["mass_earth_masses"])[:3]
    for line in map(describe, heaviest):
        print(f"      {line}")


def report_function_arguments(catalog):
    """Criterion 6."""
    banner("Criterion 6: functions that accept another function as an argument")

    # apply_to_leaves() takes a function and applies it through the recursion.
    sample = catalog["astronomical_catalog"]["galaxies"][0]
    first_planet = lambda galaxy: galaxy["star_systems"][0]["planets"][0]

    rounded = apply_to_leaves(sample, lambda v: round(v, 1) if isinstance(v, float) else v)
    print(f"  Planet radii before rounding: "
          f"{first_planet(sample)['radius_earth_radii']}")
    print(f"  Planet radii after rounding:  "
          f"{first_planet(rounded)['radius_earth_radii']}")

    shouted = apply_to_leaves(sample, lambda v: v.upper() if isinstance(v, str) else v)
    print(f"  After uppercase pass: {shouted['name']} / {first_planet(shouted)['type']}")
    print(f"  Original left unmodified: {sample['name']}")

    # summarize_by() takes three functions and composes them.
    planets = collect_dicts_with(catalog, "planet_id")
    heaviest_by_type = summarize_by(
        planets,
        key_func=lambda p: p.get("type", "unclassified"),
        value_func=lambda p: p["mass_earth_masses"],
        combine=lambda a, b: max(a, b),
    )
    print("  Heaviest planet mass per type:")
    for planet_type, mass in sorted(heaviest_by_type.items()):
        print(f"      {planet_type:<16} {mass:>8.2f} Earth masses")

    # The same function, given different arguments, answers a different question.
    count_by_type = summarize_by(
        planets,
        key_func=lambda p: p.get("type", "unclassified"),
        value_func=lambda p: 1,
        combine=lambda a, b: a + b,
    )
    print(f"  Planet count per type: {count_by_type}")


def main():
    try:
        catalog = load_catalog()
    except CatalogError as exc:
        print(f"Could not start: {exc}")
        return 1

    name = catalog["astronomical_catalog"]["catalog_name"]
    print(f"CS 660 Module Four Activity - data set: {name}")

    report_invalid_inputs(catalog)
    report_nested_search(catalog)
    report_leaves(catalog)
    report_planets(catalog)
    report_function_arguments(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
