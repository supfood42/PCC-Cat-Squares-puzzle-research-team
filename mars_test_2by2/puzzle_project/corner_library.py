import json
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent

CORNER_LIBRARY_FILE = (
    PROJECT_FOLDER
    / "unique_valid_corner_sets.json"
)


def load_saved_corner_sets(
    filename: Path = CORNER_LIBRARY_FILE,
) -> list[tuple[int, int, int, int]]:
    """
    Load the 4096 fixed-orientation corner sets
    from the JSON file.
    """

    if not filename.exists():
        raise FileNotFoundError(
            "Corner library JSON file not found:\n"
            f"{filename}\n\n"
            "Run code2_generate_corner_sets.py first."
        )

    with filename.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if "valid_sets" not in data:
        raise KeyError(
            "The JSON file does not contain "
            "'valid_sets'."
        )

    saved_sets = []

    for index, corner_set in enumerate(
        data["valid_sets"],
        start=1,
    ):
        if (
            not isinstance(corner_set, list)
            or len(corner_set) != 4
        ):
            raise ValueError(
                f"Invalid corner set at entry "
                f"{index}: {corner_set}"
            )

        saved_sets.append(
            tuple(corner_set)
        )

    return saved_sets


def build_corner_library(
    saved_sets: list[
        tuple[int, int, int, int]
    ],
) -> dict:
    """
    Build fixed-orientation lookup structures.

    Rotations are not merged.
    """

    oriented_sets = set()
    sets_by_first_corner = {}
    sets_by_first_two_corners = {}

    for saved_set in saved_sets:
        oriented_set = tuple(
            saved_set
        )

        oriented_sets.add(
            oriented_set
        )

        first_corner = (
            oriented_set[0]
        )

        sets_by_first_corner.setdefault(
            first_corner,
            set(),
        ).add(
            oriented_set
        )

        first_two = (
            oriented_set[0],
            oriented_set[1],
        )

        sets_by_first_two_corners.setdefault(
            first_two,
            set(),
        ).add(
            oriented_set
        )

    return {
        "oriented_sets": oriented_sets,
        "sets_by_first_corner": (
            sets_by_first_corner
        ),
        "sets_by_first_two_corners": (
            sets_by_first_two_corners
        ),
    }


def load_corner_library() -> dict:
    """
    Load the JSON file and return the complete
    fixed-orientation corner library.
    """

    saved_sets = load_saved_corner_sets()

    library = build_corner_library(
        saved_sets
    )

    if len(library["oriented_sets"]) != 4096:
        raise AssertionError(
            "Corner library should contain "
            f"4096 oriented sets, but contains "
            f"{len(library['oriented_sets'])}."
        )

    return library