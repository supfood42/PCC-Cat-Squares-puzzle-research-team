import json
import time
from itertools import permutations
from pathlib import Path

# Import conversion functions from Code 1.
from code1_convert_pieces import (
    convert_pieces,
    corner_id_to_pair,
    parse_multiline_input,
)


# ============================================================
# FILE SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent

VALID_SETS_FILE = (
    PROJECT_FOLDER
    / "unique_valid_corner_sets.json"
)


# ============================================================
# LOAD VALID CORNER SETS CREATED BY CODE 2
# ============================================================

def load_valid_sets() -> list[list[int]]:
    """
    Load the permanent valid-corner library created by Code 2.
    """

    if not VALID_SETS_FILE.exists():
        raise FileNotFoundError(
            "The valid-corner file was not found.\n"
            f"Expected location:\n{VALID_SETS_FILE}\n\n"
            "Run Code 2 first."
        )

    with VALID_SETS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    if "valid_sets" not in data:
        raise KeyError(
            "The JSON file does not contain 'valid_sets'."
        )

    return data["valid_sets"]


# ============================================================
# GET ORIGINAL PUZZLE-PIECE INPUT
# ============================================================

def get_original_piece_input() -> list[list[int]]:
    """
    Read the original edge data.

    Each piece must be entered as:
        top right bottom left

    A blank line ends the input.
    """

    print("Paste the four puzzle pieces below.")
    print("Use one piece per line in this order:")
    print("top right bottom left")
    print()
    print("Example:")
    print("-2 4 -2 -4")
    print("-2 -2 -1 2")
    print("-4 -4 -1 -2")
    print("2 2 2 3")
    print()
    print("Press Enter on a blank line when finished.")
    print()

    lines = []

    while True:
        line = input()

        if not line.strip():
            break

        lines.append(line)

    text = "\n".join(lines)

    pieces = parse_multiline_input(text)

    if len(pieces) != 4:
        raise ValueError(
            "A 2 × 2 puzzle requires exactly four pieces. "
            f"You entered {len(pieces)}."
        )

    return pieces


# ============================================================
# ROTATION FUNCTIONS
# ============================================================

def rotations(values) -> list[tuple]:
    """
    Return all four clockwise rotations.

    Example:
        [17, 1, 37, 39]

    becomes:
        (17, 1, 37, 39)
        (1, 37, 39, 17)
        (37, 39, 17, 1)
        (39, 17, 1, 37)
    """

    values = list(values)

    return [
        tuple(values[shift:] + values[:shift])
        for shift in range(4)
    ]


def canonical_solution_key(
    required_corners,
    piece_order
) -> tuple:
    """
    Give all rotations of the same physical solution one
    standard identity.

    This prevents the same solution from being counted four
    times merely because the entire puzzle was rotated.
    """

    corner_list = list(required_corners)
    piece_list = list(piece_order)

    equivalent_rotations = []

    for shift in range(4):
        rotated_corners = tuple(
            corner_list[shift:]
            + corner_list[:shift]
        )

        rotated_pieces = tuple(
            piece_list[shift:]
            + piece_list[:shift]
        )

        equivalent_rotations.append(
            (
                rotated_corners,
                rotated_pieces,
            )
        )

    return min(equivalent_rotations)


# ============================================================
# FIND VALID 2 × 2 SOLUTIONS
# ============================================================

def find_solutions(
    corner_pieces: list[list[int]],
    valid_sets: list[list[int]],
) -> list[dict]:
    """
    Find all valid center-corner arrangements.

    Every solution must use:
        - exactly one corner from Piece 1;
        - exactly one corner from Piece 2;
        - exactly one corner from Piece 3;
        - exactly one corner from Piece 4.

    No piece can be used twice in the same solution.
    """

    solutions = []
    seen_solutions = set()

    # Every permutation contains each piece exactly once.
    #
    # Example:
    #     (0, 1, 2, 3)
    #     (0, 2, 3, 1)
    #
    # Therefore, one solution cannot take two corners
    # from the same piece.
    all_piece_orders = permutations(range(4))

    # Convert to a list because permutations() is an iterator
    # that would otherwise be exhausted after one use.
    all_piece_orders = list(all_piece_orders)

    for saved_set in valid_sets:

        # Code 2 stores only one rotational form of each set.
        # Restore its four possible physical orientations here.
        for required_corners in rotations(saved_set):

            for piece_order in all_piece_orders:

                works = True

                for position in range(4):
                    piece_index = piece_order[position]
                    required_corner = required_corners[position]

                    if required_corner not in corner_pieces[piece_index]:
                        works = False
                        break

                if not works:
                    continue

                # Remove duplicate solutions caused only by
                # rotating the whole 2 × 2 puzzle.
                solution_key = canonical_solution_key(
                    required_corners,
                    piece_order,
                )

                if solution_key in seen_solutions:
                    continue

                seen_solutions.add(solution_key)

                solutions.append({
                    "corner_ids": list(required_corners),

                    "corner_pairs": [
                        corner_id_to_pair(corner_id)
                        for corner_id in required_corners
                    ],

                    "piece_order": [
                        piece_index + 1
                        for piece_index in piece_order
                    ],
                })

    return solutions


# ============================================================
# DISPLAY ONE SOLUTION
# ============================================================

def print_solution(
    solution: dict,
    solution_number: int,
) -> None:
    """
    Display one solution using both corner IDs and the
    original -4 to 4 values.
    """

    corner_ids = solution["corner_ids"]
    corner_pairs = solution["corner_pairs"]
    piece_order = solution["piece_order"]

    position_names = [
        "top-left",
        "top-right",
        "bottom-right",
        "bottom-left",
    ]

    print()
    print(f"Solution {solution_number}")
    print("-" * 55)

    print(f"Corner IDs: {corner_ids}")
    print(f"Corner pairs: {corner_pairs}")
    print(f"Clockwise piece order: {piece_order}")

    print("\nAssignments:")

    for position in range(4):
        print(
            f"  {position_names[position]} position: "
            f"Piece {piece_order[position]} uses "
            f"corner {corner_pairs[position]} "
            f"(ID {corner_ids[position]})"
        )


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> None:
    # Measures everything, including user input time.
    total_start_time = time.perf_counter()

    try:
        valid_sets = load_valid_sets()

        original_pieces = get_original_piece_input()

        # Code 3 passes the original data into Code 1.
        conversion_start_time = time.perf_counter()

        corner_pieces = convert_pieces(
            original_pieces
        )

        conversion_end_time = time.perf_counter()

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"\nError: {error}")
        return

    print("\nConverted by Code 1:")
    print("-" * 55)

    for piece_number, (edges, corners) in enumerate(
        zip(original_pieces, corner_pieces),
        start=1,
    ):
        print(
            f"Piece {piece_number}: "
            f"{edges} -> {corners}"
        )

    # Measure only the solution-search calculation.
    search_start_time = time.perf_counter()

    solutions = find_solutions(
        corner_pieces,
        valid_sets,
    )

    search_end_time = time.perf_counter()

    print("\n" + "=" * 55)

    if not solutions:
        print("NO SOLUTIONS")
        print(
            "The four pieces cannot each contribute one "
            "corner to a valid center arrangement."
        )

    elif len(solutions) == 1:
        print("ONE UNIQUE SOLUTION FOUND")
        print_solution(solutions[0], 1)

    else:
        print(
            f"MULTIPLE UNIQUE SOLUTIONS FOUND: "
            f"{len(solutions)}"
        )

        for solution_number, solution in enumerate(
            solutions,
            start=1,
        ):
            print_solution(
                solution,
                solution_number,
            )

    total_end_time = time.perf_counter()

    conversion_time = (
        conversion_end_time
        - conversion_start_time
    )

    search_time = (
        search_end_time
        - search_start_time
    )

    total_time = (
        total_end_time
        - total_start_time
    )

    print("\n" + "=" * 55)
    print("TIMING RESULTS")
    print("-" * 55)

    print(
        f"Code 1 conversion time: "
        f"{conversion_time:.6f} seconds"
    )

    print(
        f"Solution search time: "
        f"{search_time:.6f} seconds"
    )

    print(
        f"Total runtime, including input and output: "
        f"{total_time:.6f} seconds"
    )


if __name__ == "__main__":
    main()