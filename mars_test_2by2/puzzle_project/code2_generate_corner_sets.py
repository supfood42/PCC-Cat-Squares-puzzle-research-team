import json
from pathlib import Path

from code1_convert_pieces import (
    pair_to_corner_id,
    corner_id_to_pair,
)


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent

JSON_OUTPUT_FILE = (
    PROJECT_FOLDER
    / "unique_valid_corner_sets.json"
)

TEXT_OUTPUT_FILE = (
    PROJECT_FOLDER
    / "unique_valid_corner_sets.txt"
)

REPORT_FILE = (
    PROJECT_FOLDER
    / "corner_set_generation_report.txt"
)


# The exact order used by the corner-ID chart.
VALUE_ORDER = [
    1,
    2,
    3,
    4,
    -1,
    -2,
    -3,
    -4,
]


# ============================================================
# GENERATE ONE LOCAL JUNCTION
# ============================================================

def generate_corner_set(
    a: int,
    b: int,
    c: int,
    d: int,
) -> tuple[int, int, int, int]:
    """
    Generate one fixed-orientation internal junction.

    The four corner pairs are:

        A = [a, b]
        B = [c, d]
        C = [-b, -c]
        D = [-d, -a]

    The returned order is fixed:

        A = top-left piece's bottom-right corner
        B = top-right piece's bottom-left corner
        C = bottom-right piece's top-left corner
        D = bottom-left piece's top-right corner

    This order must not be rotationally canonicalized.
    """

    corner_a = pair_to_corner_id(
        a,
        b,
    )

    corner_b = pair_to_corner_id(
        c,
        d,
    )

    corner_c = pair_to_corner_id(
        -b,
        -c,
    )

    corner_d = pair_to_corner_id(
        -d,
        -a,
    )

    return (
        corner_a,
        corner_b,
        corner_c,
        corner_d,
    )


# ============================================================
# GENERATE ALL 4096 ORIENTED SETS
# ============================================================

def generate_all_oriented_corner_sets(
) -> list[tuple[int, int, int, int]]:
    """
    Generate all fixed-orientation local junctions.

    There are four independent variables:

        a, b, c, d

    Each has eight possible values.

        8 x 8 x 8 x 8 = 4096

    Rotations are intentionally treated as different.
    """

    valid_sets = []

    for a in VALUE_ORDER:
        for b in VALUE_ORDER:
            for c in VALUE_ORDER:
                for d in VALUE_ORDER:
                    corner_set = generate_corner_set(
                        a,
                        b,
                        c,
                        d,
                    )

                    valid_sets.append(
                        corner_set
                    )

    return valid_sets


# ============================================================
# VERIFY COMPLETENESS
# ============================================================

def verify_generated_sets(
    valid_sets: list[
        tuple[int, int, int, int]
    ],
) -> None:
    """
    Confirm that all 4096 possibilities were generated
    and that no two fixed-orientation sets are identical.
    """

    expected_count = (
        len(VALUE_ORDER) ** 4
    )

    actual_count = len(
        valid_sets
    )

    unique_count = len(
        set(valid_sets)
    )

    if actual_count != expected_count:
        raise AssertionError(
            "Incorrect generated-set count.\n"
            f"Expected: {expected_count}\n"
            f"Generated: {actual_count}"
        )

    if unique_count != expected_count:
        raise AssertionError(
            "Some oriented sets were duplicated.\n"
            f"Expected unique sets: {expected_count}\n"
            f"Actual unique sets: {unique_count}"
        )

    for index, corner_set in enumerate(
        valid_sets,
        start=1,
    ):
        if len(corner_set) != 4:
            raise AssertionError(
                f"Set {index} does not contain "
                f"exactly four corners."
            )

        for corner_id in corner_set:
            if not 1 <= corner_id <= 64:
                raise AssertionError(
                    f"Set {index} contains invalid "
                    f"corner ID {corner_id}."
                )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    valid_sets: list[
        tuple[int, int, int, int]
    ],
) -> None:
    """
    Save all 4096 oriented sets in machine-readable form.
    """

    data = {
        "description": (
            "All valid fixed-orientation internal "
            "four-corner junctions."
        ),
        "orientation_order": [
            (
                "top-left piece bottom-right corner"
            ),
            (
                "top-right piece bottom-left corner"
            ),
            (
                "bottom-right piece top-left corner"
            ),
            (
                "bottom-left piece top-right corner"
            ),
        ],
        "rotations_are_distinct": True,
        "value_order": VALUE_ORDER,
        "total_sets": len(valid_sets),
        "valid_sets": [
            list(corner_set)
            for corner_set in valid_sets
        ],
    }

    with JSON_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
        )


# ============================================================
# SAVE READABLE TEXT FILE
# ============================================================

def save_text(
    valid_sets: list[
        tuple[int, int, int, int]
    ],
) -> None:
    """
    Save a readable numbered list of all oriented sets.
    """

    lines = [
        "ALL FIXED-ORIENTATION VALID CORNER SETS",
        "=" * 80,
        "",
        (
            "Order:"
        ),
        (
            "A = top-left piece bottom-right corner"
        ),
        (
            "B = top-right piece bottom-left corner"
        ),
        (
            "C = bottom-right piece top-left corner"
        ),
        (
            "D = bottom-left piece top-right corner"
        ),
        "",
        (
            "Rotated versions are stored separately."
        ),
        (
            f"Total sets: {len(valid_sets)}"
        ),
        "",
        "NUMBER    CORNER IDS",
        "-" * 80,
    ]

    for set_number, corner_set in enumerate(
        valid_sets,
        start=1,
    ):
        lines.append(
            f"{set_number:<9} "
            f"{list(corner_set)}"
        )

    lines.extend([
        "",
        "=" * 80,
        "END OF CORNER SETS",
        "",
    ])

    with TEXT_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join(lines)
        )


# ============================================================
# OPTIONAL DETAILED REPORT
# ============================================================

def save_generation_report(
    valid_sets: list[
        tuple[int, int, int, int]
    ],
) -> None:
    """
    Save examples with both corner IDs and decoded pairs.
    """

    lines = [
        "CORNER SET GENERATION REPORT",
        "=" * 80,
        "",
        (
            f"Total generated sets: "
            f"{len(valid_sets)}"
        ),
        (
            f"Total unique oriented sets: "
            f"{len(set(valid_sets))}"
        ),
        "",
        (
            "Rotations were not combined."
        ),
        "",
        "FIRST 25 SETS",
        "-" * 80,
    ]

    for index, corner_set in enumerate(
        valid_sets[:25],
        start=1,
    ):
        decoded_pairs = [
            list(
                corner_id_to_pair(
                    corner_id
                )
            )
            for corner_id in corner_set
        ]

        lines.extend([
            f"Set {index}",
            (
                f"  Corner IDs: "
                f"{list(corner_set)}"
            ),
            (
                f"  Corner pairs: "
                f"{decoded_pairs}"
            ),
            "",
        ])

    lines.extend([
        "LAST 25 SETS",
        "-" * 80,
    ])

    start_number = (
        len(valid_sets)
        - 24
    )

    for offset, corner_set in enumerate(
        valid_sets[-25:],
    ):
        set_number = (
            start_number
            + offset
        )

        decoded_pairs = [
            list(
                corner_id_to_pair(
                    corner_id
                )
            )
            for corner_id in corner_set
        ]

        lines.extend([
            f"Set {set_number}",
            (
                f"  Corner IDs: "
                f"{list(corner_set)}"
            ),
            (
                f"  Corner pairs: "
                f"{decoded_pairs}"
            ),
            "",
        ])

    lines.extend([
        "=" * 80,
        "END OF REPORT",
        "",
    ])

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join(lines)
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    valid_sets = (
        generate_all_oriented_corner_sets()
    )

    verify_generated_sets(
        valid_sets
    )

    save_json(
        valid_sets
    )

    save_text(
        valid_sets
    )

    save_generation_report(
        valid_sets
    )

    print(
        "Corner-set generation completed."
    )

    print(
        f"Generated sets: "
        f"{len(valid_sets)}"
    )

    print(
        f"Unique oriented sets: "
        f"{len(set(valid_sets))}"
    )

    print(
        "\nRotations were preserved as "
        "separate possibilities."
    )

    print(
        f"\nJSON file:\n"
        f"{JSON_OUTPUT_FILE}"
    )

    print(
        f"\nText file:\n"
        f"{TEXT_OUTPUT_FILE}"
    )

    print(
        f"\nReport file:\n"
        f"{REPORT_FILE}"
    )


if __name__ == "__main__":
    main()