import math
import random
import re
import sys
import time
from typing import List, Optional

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SOLVE_MULTIPLE_PUZZLES = False
# A positive value means one cat side and a negative value means the opposite side;
# the absolute value is the color number (1..4).

def rotate_piece(piece: List[int], times: int = 1) -> List[int]:
    # Rotate a piece clockwise by the requested number of quarter turns.
    rotated = list(piece)
    for _ in range(times % 4):
        rotated = [rotated[3], rotated[0], rotated[1], rotated[2]]
    return rotated

def build_rotations(pieces: List[List[int]]) -> List[List[List[int]]]:
    # Return every rotation for every piece.
    rotations: List[List[List[int]]] = []
    for piece in pieces:
        options: List[List[int]] = []
        current = list(piece)
        for _ in range(4):
            options.append(current)
            current = rotate_piece(current)
        rotations.append(options)
    return rotations

def matches(left: Optional[int], right: Optional[int]) -> bool:
    # Check whether two sides form a valid cat-head/cat-body match.
    return (
        left is not None
        and right is not None
        and abs(left) == abs(right)
        and left + right == 0
    )

def solve_puzzle_with_stats(pieces: List[List[int]]):
    # Solve an nxn matched-squares puzzle using backtracking and count every solution.
    if not pieces:
        return None

    count = len(pieces)
    n = int(round(math.sqrt(count)))
    if n * n != count:
        raise ValueError(f"The number of pieces ({count}) must form a perfect square grid")

    # Print the start sequence matching your style
    print("\n[Running] Initiating solver and mapping layers...")

    rotations = build_rotations(pieces)
    board: List[List[Optional[dict]]] = [[None] * n for _ in range(n)]
    used = [False] * count
    start_time = time.perf_counter()
    steps = 0
    solution_count = 0
    first_solution_grid: Optional[List[List[List[int]]]] = None
    rng = random.Random(0)

    def backtrack(position: int) -> None:
        nonlocal steps, solution_count, first_solution_grid
        steps += 1

        if position == count:
            solution_count += 1
            if solution_count == 1:
                first_solution_grid = [[board[row][col]["piece"] for col in range(n)] for row in range(n)]
            return

        row, col = divmod(position, n)
        candidate_indices = list(range(count))
        rng.shuffle(candidate_indices)

        for piece_index in candidate_indices:
            if used[piece_index]:
                continue

            rotation_order = list(range(4))
            rng.shuffle(rotation_order)
            for rotation_index in rotation_order:
                rotated_piece = rotations[piece_index][rotation_index]

                if row > 0:
                    above = board[row - 1][col]
                    if above is not None and not matches(rotated_piece[0], above["piece"][2]):
                        continue

                if col > 0:
                    left = board[row][col - 1]
                    if left is not None and not matches(rotated_piece[3], left["piece"][1]):
                        continue

                board[row][col] = {
                    "piece": rotated_piece,
                    "index": piece_index,
                    "rotation": rotation_index,
                }
                used[piece_index] = True

                backtrack(position + 1)

                used[piece_index] = False
                board[row][col] = None

    backtrack(0)
    elapsed_seconds = time.perf_counter() - start_time

    # Print the end sequence matching your style (with clear line padding)
    print("\r" + " " * 50 + "\r", end="") 
    print("[Done] Search finished.                           ")
    print(f"Total states explored: {steps:,}")
    print(f"Time elapsed: {elapsed_seconds:.4f} seconds")
    print(f"Solutions found: {solution_count:,}")

    if solution_count == 0:
        return {
            "grid": None,
            "solution_count": 0,
            "steps": steps,
            "elapsed_ms": elapsed_seconds * 1000.0,
        }

    return {
        "grid": first_solution_grid,
        "solution_count": solution_count,
        "steps": steps,
        "elapsed_ms": elapsed_seconds * 1000.0,
    }

def solve_puzzle(pieces: List[List[int]]):
    # Convenience wrapper that returns only the first solved grid when one exists.
    result = solve_puzzle_with_stats(pieces)
    return None if result is None or result["grid"] is None else result["grid"]

def parse_pieces(text: str) -> List[List[int]]:
    # Parse all integers from the input and group them into four-value pieces.
    tokens = re.findall(r"-?\d+", text)
    values = [int(token) for token in tokens]
    return [values[i : i + 4] for i in range(0, len(values), 4)]

def print_solution(grid: List[List[List[int]]]) -> None:
    # Print the solved grid as one piece per line without blank lines.
    for row in grid:
        for piece in row:
            print(*piece)

def main() -> None:
    print("Input puzzle pieces as integers, one row per line or as a space-separated list.")
    print("Press Enter twice to finish:")
    lines = []
    while True:
        line = sys.stdin.readline()
        if line == "":
            break
        stripped = line.strip()
        if not stripped:
            break
        lines.append(stripped)

    text = "\n".join(lines)
    if not text and len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])

    pieces = parse_pieces(text)
    if not pieces:
        print("No pieces entered. Exiting.")
        sys.exit(0)

    result = solve_puzzle_with_stats(pieces)

    if result and result["grid"] is not None:
        print(f"\nFound {result['solution_count']} solution(s).")
        print("First solution:")
        print_solution(result["grid"])
    else:
        print("\nNo solution exists for this configuration.")

if __name__ == "__main__":
    main()