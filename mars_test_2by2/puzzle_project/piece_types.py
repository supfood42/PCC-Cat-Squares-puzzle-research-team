from collections import Counter
from pathlib import Path

from code1_convert_pieces import piece_to_corners
from puzzle_checks import (
    determine_board_size,
    parse_piece_text,
    run_global_checks,
)


# ============================================================
# FILE SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_FOLDER / "piece_type_report.txt"


# ============================================================
# ROTATION FUNCTIONS
# ============================================================

def rotate_edges_clockwise(
    edges: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """
    Rotate one piece 90 degrees clockwise.

    Edge order:
        top, right, bottom, left
    """

    top, right, bottom, left = edges

    return (
        left,
        top,
        right,
        bottom,
    )


def get_all_rotations(
    edges: list[int] | tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    """
    Return all four rotations, including repeated rotations.
    """

    current = tuple(edges)
    rotations = []

    for _ in range(4):
        rotations.append(current)
        current = rotate_edges_clockwise(current)

    return rotations


def get_unique_rotations(
    edges: list[int] | tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    """
    Return only distinct rotations.
    """

    unique_rotations = []
    seen = set()

    for rotation in get_all_rotations(edges):
        if rotation not in seen:
            seen.add(rotation)
            unique_rotations.append(rotation)

    return unique_rotations


def canonical_piece(
    edges: list[int] | tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """
    Give all rotationally equivalent pieces the same identity.
    """

    return min(get_all_rotations(edges))


# ============================================================
# BUILD PIECE TYPES
# ============================================================

def build_piece_types(
    pieces: list[list[int]]
) -> list[dict]:
    """
    Group pieces that are identical after rotation.
    """

    grouped_pieces: dict[
        tuple[int, int, int, int],
        list[int]
    ] = {}

    for piece_number, edges in enumerate(
        pieces,
        start=1,
    ):
        canonical_edges = canonical_piece(edges)

        grouped_pieces.setdefault(
            canonical_edges,
            [],
        ).append(piece_number)

    piece_types = []

    for type_id, (
        canonical_edges,
        source_piece_numbers,
    ) in enumerate(
        sorted(grouped_pieces.items()),
        start=1,
    ):
        rotations = []

        for rotation_id, rotated_edges in enumerate(
            get_unique_rotations(canonical_edges)
        ):
            corner_ids = tuple(
                piece_to_corners(list(rotated_edges))
            )

            rotations.append({
                "rotation_id": rotation_id,
                "edges": rotated_edges,
                "corners": corner_ids,
            })

        piece_types.append({
            "type_id": type_id,
            "canonical_edges": canonical_edges,
            "count": len(source_piece_numbers),
            "remaining_count": len(source_piece_numbers),
            "source_piece_numbers": source_piece_numbers,
            "rotations": rotations,
        })

    return piece_types


def create_piece_inventory(
    piece_types: list[dict],
) -> Counter:
    """
    Create the piece-type inventory for the future solver.
    """

    return Counter({
        piece_type["type_id"]: piece_type["count"]
        for piece_type in piece_types
    })


def count_total_rotated_candidates(
    piece_types: list[dict],
) -> int:
    """
    Count distinct piece-type and rotation candidates.
    """

    return sum(
        len(piece_type["rotations"])
        for piece_type in piece_types
    )


# ============================================================
# REPORT FILE
# ============================================================

def write_piece_type_report(
    pieces: list[list[int]],
    piece_types: list[dict],
    inventory: Counter,
) -> None:
    """
    Overwrite the report file with the latest run.
    """

    n = determine_board_size(len(pieces))

    duplicate_count = (
        len(pieces)
        - len(piece_types)
    )

    lines = [
        "PUZZLE PIECE-TYPE REPORT",
        "=" * 70,
        "",
        f"Board size: {n} x {n}",
        f"Physical pieces: {len(pieces)}",
        f"Distinct piece types: {len(piece_types)}",
        (
            "Duplicate physical pieces grouped together: "
            f"{duplicate_count}"
        ),
        (
            "Distinct piece-type/rotation candidates: "
            f"{count_total_rotated_candidates(piece_types)}"
        ),
        "",
        "INITIAL PIECE-TYPE INVENTORY",
        "-" * 70,
    ]

    for type_id, count in sorted(inventory.items()):
        lines.append(
            f"Type {type_id}: {count} physical copy/copies"
        )

    for piece_type in piece_types:
        lines.extend([
            "",
            "=" * 70,
            f"PIECE TYPE {piece_type['type_id']}",
            "-" * 70,
            (
                "Number of physical copies: "
                f"{piece_type['count']}"
            ),
            (
                "Original piece numbers: "
                f"{piece_type['source_piece_numbers']}"
            ),
            (
                "Canonical edges "
                "[top, right, bottom, left]: "
                f"{list(piece_type['canonical_edges'])}"
            ),
            (
                "Number of distinct rotations: "
                f"{len(piece_type['rotations'])}"
            ),
        ])

        for rotation in piece_type["rotations"]:
            lines.extend([
                "",
                f"  Rotation {rotation['rotation_id']}",
                (
                    "    Edges "
                    "[top, right, bottom, left]: "
                    f"{list(rotation['edges'])}"
                ),
                (
                    "    Corners "
                    "[top-left, top-right, "
                    "bottom-right, bottom-left]: "
                    f"{list(rotation['corners'])}"
                ),
            ])

    lines.extend([
        "",
        "=" * 70,
        "END OF REPORT",
        "",
    ])

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(lines))


def ask_whether_to_delete_report() -> None:
    """
    Delete the temporary report only after confirmation.
    """

    print()
    answer = input(
        "Delete the report file now? "
        "Enter y to delete it, or press Enter to keep it: "
    ).strip().lower()

    if answer in {"y", "yes"}:
        try:
            REPORT_FILE.unlink()
            print("Report file deleted.")
        except FileNotFoundError:
            print("The report file was already absent.")
    else:
        print("Report file kept.")


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
    inventory = create_piece_inventory(piece_types)

    write_piece_type_report(
        pieces,
        piece_types,
        inventory,
    )

    n = determine_board_size(len(pieces))

    # Only a brief summary is printed in the terminal.
    print("\nProcessing completed.")
    print(f"Board size: {n} x {n}")
    print(f"Physical pieces: {len(pieces)}")
    print(f"Distinct piece types: {len(piece_types)}")
    print(
        "Distinct type/rotation candidates: "
        f"{count_total_rotated_candidates(piece_types)}"
    )
    print(f"\nDetailed report written to:\n{REPORT_FILE}")

    ask_whether_to_delete_report()


if __name__ == "__main__":
    main()