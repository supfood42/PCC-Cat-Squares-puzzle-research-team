from pathlib import Path

from piece_types import (
    build_piece_types,
    parse_piece_text,
    run_global_checks,
)


PROJECT_FOLDER = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_FOLDER / "compatibility_report.txt"


# ============================================================
# BASIC EDGE MATCHING
# ============================================================

def edges_match(first_edge: int, second_edge: int) -> bool:
    """
    Two touching edges match when they have the same color
    and opposite signs.

    Examples:
        2 matches -2
        -4 matches 4

    These do not match:
        2 and 2
        2 and -3
    """

    return first_edge == -second_edge


# ============================================================
# CANDIDATE IDENTITIES
# ============================================================

def candidate_key(
    type_id: int,
    rotation_id: int,
) -> tuple[int, int]:
    """
    Identify one piece type in one particular rotation.
    """

    return type_id, rotation_id


def build_candidate_records(
    piece_types: list[dict],
) -> dict[tuple[int, int], dict]:
    """
    Flatten all piece types and rotations into one lookup.

    Key:
        (type_id, rotation_id)

    Value:
        {
            "type_id": ...,
            "rotation_id": ...,
            "edges": (...),
            "corners": (...),
            "count": ...
        }
    """

    candidates = {}

    for piece_type in piece_types:
        type_id = piece_type["type_id"]

        for rotation in piece_type["rotations"]:
            rotation_id = rotation["rotation_id"]

            key = candidate_key(
                type_id,
                rotation_id,
            )

            candidates[key] = {
                "type_id": type_id,
                "rotation_id": rotation_id,
                "edges": tuple(rotation["edges"]),
                "corners": tuple(rotation["corners"]),
                "count": piece_type["count"],
            }

    return candidates


# ============================================================
# BUILD EDGE INDEXES
# ============================================================

def build_edge_indexes(
    candidates: dict[tuple[int, int], dict],
) -> dict:
    """
    Group rotated candidates according to the value
    appearing on each side.

    Example:
        by_left_edge[-2]

    returns every rotated candidate whose left edge is -2.
    """

    indexes = {
        "by_top_edge": {},
        "by_right_edge": {},
        "by_bottom_edge": {},
        "by_left_edge": {},
    }

    for key, candidate in candidates.items():
        top, right, bottom, left = candidate["edges"]

        indexes["by_top_edge"].setdefault(
            top,
            set(),
        ).add(key)

        indexes["by_right_edge"].setdefault(
            right,
            set(),
        ).add(key)

        indexes["by_bottom_edge"].setdefault(
            bottom,
            set(),
        ).add(key)

        indexes["by_left_edge"].setdefault(
            left,
            set(),
        ).add(key)

    return indexes


# ============================================================
# BUILD NEIGHBOR COMPATIBILITY
# ============================================================

def build_compatibility(
    candidates: dict[tuple[int, int], dict],
    edge_indexes: dict,
) -> dict:
    """
    For every rotated candidate, store which rotated candidates
    may legally appear above, right, below, and left.

    Piece A can have Piece B on its right when:

        A.right == -B.left

    Similar rules apply for the other directions.
    """

    compatibility = {}

    for key, candidate in candidates.items():
        top, right, bottom, left = candidate["edges"]

        allowed_above = set(
            edge_indexes["by_bottom_edge"].get(
                -top,
                set(),
            )
        )

        allowed_right = set(
            edge_indexes["by_left_edge"].get(
                -right,
                set(),
            )
        )

        allowed_below = set(
            edge_indexes["by_top_edge"].get(
                -bottom,
                set(),
            )
        )

        allowed_left = set(
            edge_indexes["by_right_edge"].get(
                -left,
                set(),
            )
        )

        compatibility[key] = {
            "above": allowed_above,
            "right": allowed_right,
            "below": allowed_below,
            "left": allowed_left,
        }

    return compatibility


# ============================================================
# DIRECT LOOKUP FUNCTIONS
# ============================================================

def candidates_with_left_edge(
    required_value: int,
    edge_indexes: dict,
) -> set[tuple[int, int]]:
    """
    Return candidates whose left edge equals required_value.
    """

    return set(
        edge_indexes["by_left_edge"].get(
            required_value,
            set(),
        )
    )


def candidates_with_top_edge(
    required_value: int,
    edge_indexes: dict,
) -> set[tuple[int, int]]:
    """
    Return candidates whose top edge equals required_value.
    """

    return set(
        edge_indexes["by_top_edge"].get(
            required_value,
            set(),
        )
    )


def candidates_matching_left_neighbor(
    left_candidate_key: tuple[int, int],
    compatibility: dict,
) -> set[tuple[int, int]]:
    """
    Return candidates that may be placed directly to the right
    of a known left-side candidate.
    """

    return set(
        compatibility[left_candidate_key]["right"]
    )


def candidates_matching_upper_neighbor(
    upper_candidate_key: tuple[int, int],
    compatibility: dict,
) -> set[tuple[int, int]]:
    """
    Return candidates that may be placed directly below
    a known upper candidate.
    """

    return set(
        compatibility[upper_candidate_key]["below"]
    )


def candidates_matching_both_neighbors(
    left_candidate_key: tuple[int, int],
    upper_candidate_key: tuple[int, int],
    compatibility: dict,
) -> set[tuple[int, int]]:
    """
    Return candidates that simultaneously match:
        - the piece to their left;
        - the piece above them.

    This intersection is central to the future solver.
    """

    from_left = compatibility[
        left_candidate_key
    ]["right"]

    from_above = compatibility[
        upper_candidate_key
    ]["below"]

    return set(from_left) & set(from_above)


# ============================================================
# INVENTORY FILTERING
# ============================================================

def filter_by_remaining_inventory(
    candidate_keys: set[tuple[int, int]],
    remaining_inventory: dict[int, int],
) -> set[tuple[int, int]]:
    """
    Remove candidates whose piece type has no physical copies left.

    Multiple rotations of one type share the same inventory count.
    """

    return {
        key
        for key in candidate_keys
        if remaining_inventory.get(key[0], 0) > 0
    }


# ============================================================
# TEST COMPATIBILITY DATA
# ============================================================

def run_self_tests(
    candidates: dict[tuple[int, int], dict],
    compatibility: dict,
) -> None:
    """
    Verify that every recorded neighbor relationship
    actually satisfies the edge rule.
    """

    for key, candidate in candidates.items():
        top, right, bottom, left = candidate["edges"]

        for other_key in compatibility[key]["right"]:
            other_left = candidates[other_key]["edges"][3]

            if not edges_match(right, other_left):
                raise AssertionError(
                    f"Invalid right compatibility: "
                    f"{key} -> {other_key}"
                )

        for other_key in compatibility[key]["left"]:
            other_right = candidates[other_key]["edges"][1]

            if not edges_match(left, other_right):
                raise AssertionError(
                    f"Invalid left compatibility: "
                    f"{key} -> {other_key}"
                )

        for other_key in compatibility[key]["above"]:
            other_bottom = candidates[other_key]["edges"][2]

            if not edges_match(top, other_bottom):
                raise AssertionError(
                    f"Invalid above compatibility: "
                    f"{key} -> {other_key}"
                )

        for other_key in compatibility[key]["below"]:
            other_top = candidates[other_key]["edges"][0]

            if not edges_match(bottom, other_top):
                raise AssertionError(
                    f"Invalid below compatibility: "
                    f"{key} -> {other_key}"
                )


# ============================================================
# REPORT FILE
# ============================================================

def write_compatibility_report(
    piece_types: list[dict],
    candidates: dict[tuple[int, int], dict],
    compatibility: dict,
) -> Path:
    """
    Overwrite the detailed compatibility report.
    """

    lines = [
        "PIECE COMPATIBILITY REPORT",
        "=" * 75,
        "",
        f"Distinct piece types: {len(piece_types)}",
        (
            "Distinct type-and-rotation candidates: "
            f"{len(candidates)}"
        ),
        "",
    ]

    for key in sorted(candidates):
        candidate = candidates[key]
        neighbors = compatibility[key]

        lines.extend([
            "=" * 75,
            (
                f"TYPE {candidate['type_id']}, "
                f"ROTATION {candidate['rotation_id']}"
            ),
            "-" * 75,
            (
                "Edges [top, right, bottom, left]: "
                f"{list(candidate['edges'])}"
            ),
            (
                "Corners [top-left, top-right, "
                "bottom-right, bottom-left]: "
                f"{list(candidate['corners'])}"
            ),
            (
                "Physical copies of this piece type: "
                f"{candidate['count']}"
            ),
            "",
            (
                "Compatible candidates above: "
                f"{len(neighbors['above'])}"
            ),
            (
                "Compatible candidates to the right: "
                f"{len(neighbors['right'])}"
            ),
            (
                "Compatible candidates below: "
                f"{len(neighbors['below'])}"
            ),
            (
                "Compatible candidates to the left: "
                f"{len(neighbors['left'])}"
            ),
            "",
            "Sample right-side candidates:",
        ])

        for other_key in sorted(
            neighbors["right"]
        )[:10]:
            other = candidates[other_key]

            lines.append(
                f"  Type {other['type_id']}, "
                f"rotation {other['rotation_id']}, "
                f"edges {list(other['edges'])}"
            )

        lines.append("")

    lines.extend([
        "=" * 75,
        "END OF REPORT",
        "",
    ])

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(lines))

    return REPORT_FILE


# ============================================================
# PREPARE ALL COMPATIBILITY DATA
# ============================================================

def prepare_compatibility(
    piece_types: list[dict],
) -> dict:
    """
    Reusable entry point for the future solver.

    Returns:
        candidates
        edge indexes
        compatibility relationships
    """

    candidates = build_candidate_records(
        piece_types
    )

    edge_indexes = build_edge_indexes(
        candidates
    )

    compatibility = build_compatibility(
        candidates,
        edge_indexes,
    )

    run_self_tests(
        candidates,
        compatibility,
    )

    return {
        "candidates": candidates,
        "edge_indexes": edge_indexes,
        "compatibility": compatibility,
    }


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> None:
    print("Paste all puzzle pieces.")
    print("Use one piece per line:")
    print("top right bottom left")
    print()
    print("Press Enter on a blank line when finished.")
    print()

    lines = []

    while True:
        line = input()

        if not line.strip():
            break

        lines.append(line)

    try:
        pieces = parse_piece_text(
            "\n".join(lines)
        )
    except ValueError as error:
        print(f"\nInput error: {error}")
        return

    check_result = run_global_checks(pieces)

    if not check_result["possible"]:
        print("\nNO SOLUTION")
        print(check_result["reason"])
        return

    piece_types = build_piece_types(pieces)

    try:
        prepared = prepare_compatibility(
            piece_types
        )
    except AssertionError as error:
        print(f"\nCompatibility error:\n{error}")
        return

    report_file = write_compatibility_report(
        piece_types,
        prepared["candidates"],
        prepared["compatibility"],
    )

    print("\nCompatibility indexes created successfully.")
    print(f"Distinct piece types: {len(piece_types)}")
    print(
        "Distinct type-and-rotation candidates: "
        f"{len(prepared['candidates'])}"
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