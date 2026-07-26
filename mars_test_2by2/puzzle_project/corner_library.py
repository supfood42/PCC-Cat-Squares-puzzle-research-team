import json
from pathlib import Path


# ============================================================
# FILE SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent

CORNER_LIBRARY_FILE = (
    PROJECT_FOLDER
    / "unique_valid_corner_sets.json"
)


# ============================================================
# ROTATION FUNCTIONS
# ============================================================

def rotate_corner_set(
    corners: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """
    Rotate one four-corner junction clockwise.

    Input order:
        [top-left, top-right, bottom-right, bottom-left]

    After a 90-degree clockwise rotation:
        bottom-left becomes top-left
        top-left becomes top-right
        top-right becomes bottom-right
        bottom-right becomes bottom-left
    """

    top_left, top_right, bottom_right, bottom_left = corners

    return (
        bottom_left,
        top_left,
        top_right,
        bottom_right,
    )


def get_all_corner_rotations(
    corners: list[int] | tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    """
    Return all four rotations of one corner set.
    """

    current = tuple(corners)
    rotations = []

    for _ in range(4):
        rotations.append(current)
        current = rotate_corner_set(current)

    return rotations


def get_unique_corner_rotations(
    corners: list[int] | tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    """
    Return only distinct rotations.

    Some symmetric corner sets may have fewer than
    four distinct rotations.
    """

    unique_rotations = []
    seen = set()

    for rotation in get_all_corner_rotations(corners):
        if rotation not in seen:
            seen.add(rotation)
            unique_rotations.append(rotation)

    return unique_rotations


def canonical_corner_set(
    corners: list[int] | tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """
    Give all rotations of the same physical junction
    one standard representation.

    The smallest rotation is used.
    """

    return min(get_all_corner_rotations(corners))


# ============================================================
# LOAD SAVED CORNER SETS
# ============================================================

def load_saved_corner_sets(
    filename: Path = CORNER_LIBRARY_FILE,
) -> list[tuple[int, int, int, int]]:
    """
    Load the valid corner sets created by Code 2.
    """

    if not filename.exists():
        raise FileNotFoundError(
            "The corner-library JSON file was not found.\n"
            f"Expected location:\n{filename}\n\n"
            "Run code2_generate_corner_sets.py first."
        )

    try:
        with filename.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"The JSON file could not be read: {filename}"
        ) from error

    if "valid_sets" not in data:
        raise KeyError(
            "The JSON file does not contain a 'valid_sets' section."
        )

    saved_sets = []

    for index, corners in enumerate(
        data["valid_sets"],
        start=1,
    ):
        if not isinstance(corners, list) or len(corners) != 4:
            raise ValueError(
                f"Saved set {index} is invalid: {corners}"
            )

        if any(
            not isinstance(value, int)
            or not 1 <= value <= 64
            for value in corners
        ):
            raise ValueError(
                f"Saved set {index} contains an invalid corner ID: "
                f"{corners}"
            )

        saved_sets.append(tuple(corners))

    return saved_sets


# ============================================================
# BUILD FAST LOOKUP LIBRARIES
# ============================================================

def build_corner_library(
    saved_sets: list[tuple[int, int, int, int]]
) -> dict:
    """
    Build fast lookup structures.

    canonical_sets:
        One representative for each junction,
        ignoring whole-junction rotation.

    oriented_sets:
        Every physically valid clockwise orientation.

    sets_by_first_corner:
        Quickly find junctions beginning with one corner ID.

    sets_by_first_two_corners:
        Quickly find junctions beginning with two known
        clockwise corner IDs.
    """

    canonical_sets = set()
    oriented_sets = set()

    sets_by_first_corner: dict[
        int,
        set[tuple[int, int, int, int]]
    ] = {}

    sets_by_first_two_corners: dict[
        tuple[int, int],
        set[tuple[int, int, int, int]]
    ] = {}

    for saved_set in saved_sets:
        canonical = canonical_corner_set(saved_set)
        canonical_sets.add(canonical)

        for oriented_set in get_unique_corner_rotations(saved_set):
            oriented_sets.add(oriented_set)

            first_corner = oriented_set[0]

            sets_by_first_corner.setdefault(
                first_corner,
                set(),
            ).add(oriented_set)

            first_two = (
                oriented_set[0],
                oriented_set[1],
            )

            sets_by_first_two_corners.setdefault(
                first_two,
                set(),
            ).add(oriented_set)

    return {
        "canonical_sets": canonical_sets,
        "oriented_sets": oriented_sets,
        "sets_by_first_corner": sets_by_first_corner,
        "sets_by_first_two_corners": sets_by_first_two_corners,
    }


def load_corner_library() -> dict:
    """
    Load the JSON file and build all lookup structures.
    """

    saved_sets = load_saved_corner_sets()
    return build_corner_library(saved_sets)


# ============================================================
# VALIDITY CHECKS
# ============================================================

def is_valid_oriented_junction(
    corners: list[int] | tuple[int, int, int, int],
    library: dict,
) -> bool:
    """
    Check whether the exact clockwise orientation is valid.
    """

    if len(corners) != 4:
        return False

    return tuple(corners) in library["oriented_sets"]


def is_valid_junction_ignoring_rotation(
    corners: list[int] | tuple[int, int, int, int],
    library: dict,
) -> bool:
    """
    Check whether a junction is valid when the whole junction
    may be rotated.
    """

    if len(corners) != 4:
        return False

    canonical = canonical_corner_set(corners)

    return canonical in library["canonical_sets"]


def find_sets_starting_with_corner(
    corner_id: int,
    library: dict,
) -> list[tuple[int, int, int, int]]:
    """
    Return all valid oriented junctions whose first corner
    matches corner_id.
    """

    return sorted(
        library["sets_by_first_corner"].get(
            corner_id,
            set(),
        )
    )


def find_sets_starting_with_two_corners(
    first_corner: int,
    second_corner: int,
    library: dict,
) -> list[tuple[int, int, int, int]]:
    """
    Return all valid oriented junctions beginning with
    two known clockwise corners.
    """

    return sorted(
        library["sets_by_first_two_corners"].get(
            (first_corner, second_corner),
            set(),
        )
    )


# ============================================================
# OPTIONAL REPORT
# ============================================================

def write_corner_library_report(
    library: dict,
) -> Path:
    """
    Write a compact report instead of printing the entire
    corner library in the terminal.
    """

    report_file = (
        PROJECT_FOLDER
        / "corner_library_report.txt"
    )

    lines = [
        "CORNER LIBRARY REPORT",
        "=" * 70,
        "",
        (
            "Unique junctions ignoring rotation: "
            f"{len(library['canonical_sets'])}"
        ),
        (
            "Valid oriented junctions: "
            f"{len(library['oriented_sets'])}"
        ),
        (
            "Distinct first-corner index entries: "
            f"{len(library['sets_by_first_corner'])}"
        ),
        (
            "Distinct first-two-corner index entries: "
            f"{len(library['sets_by_first_two_corners'])}"
        ),
        "",
        "SAMPLE ORIENTED JUNCTIONS",
        "-" * 70,
    ]

    for corners in sorted(
        library["oriented_sets"]
    )[:25]:
        lines.append(str(list(corners)))

    lines.extend([
        "",
        "SAMPLE FIRST-TWO-CORNER LOOKUPS",
        "-" * 70,
    ])

    for pair in sorted(
        library["sets_by_first_two_corners"]
    )[:25]:
        matches = sorted(
            library["sets_by_first_two_corners"][pair]
        )

        lines.append(
            f"{pair}: {len(matches)} matching set(s)"
        )

        for match in matches[:5]:
            lines.append(
                f"    {list(match)}"
            )

    lines.extend([
        "",
        "=" * 70,
        "END OF REPORT",
        "",
    ])

    with report_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(lines))

    return report_file


# ============================================================
# BASIC SELF-TESTS
# ============================================================

def run_self_tests(
    library: dict,
) -> None:
    """
    Test several important properties automatically.
    """

    if not library["canonical_sets"]:
        raise AssertionError(
            "The canonical corner library is empty."
        )

    if not library["oriented_sets"]:
        raise AssertionError(
            "The oriented corner library is empty."
        )

    # Every canonical set must have at least one valid orientation.
    for canonical in library["canonical_sets"]:
        rotations = get_unique_corner_rotations(canonical)

        if not any(
            rotation in library["oriented_sets"]
            for rotation in rotations
        ):
            raise AssertionError(
                f"Canonical set has no valid orientation: "
                f"{canonical}"
            )

    # Verify the example from the earlier work if it exists.
    example = (17, 1, 37, 39)

    if example in library["oriented_sets"]:
        assert is_valid_oriented_junction(
            example,
            library,
        )

        assert is_valid_junction_ignoring_rotation(
            (1, 37, 39, 17),
            library,
        )


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> None:
    try:
        library = load_corner_library()
        run_self_tests(library)
    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        AssertionError,
    ) as error:
        print(f"\nCorner-library error:\n{error}")
        return

    report_file = write_corner_library_report(
        library
    )

    print("Corner library loaded successfully.")
    print(
        "Unique junctions ignoring rotation: "
        f"{len(library['canonical_sets'])}"
    )
    print(
        "Valid oriented junctions: "
        f"{len(library['oriented_sets'])}"
    )
    print(f"\nDetailed report written to:\n{report_file}")

    answer = input(
        "\nDelete the report file now? "
        "Enter y to delete it, or press Enter to keep it: "
    ).strip().lower()

    if answer in {"y", "yes"}:
        try:
            report_file.unlink()
            print("Report file deleted.")
        except FileNotFoundError:
            print("The report file was already absent.")
    else:
        print("Report file kept.")


if __name__ == "__main__":
    main()