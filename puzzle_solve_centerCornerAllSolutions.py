import math
import os
import random
import re
import sys
import time
import tkinter as tk
from tkinter import filedialog
from typing import List, Optional, Tuple

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SOLVE_MULTIPLE_PUZZLES = True
FIND_ALL_SOLUTIONS = True  # Set to True to find all solutions for each puzzle
# ==============================================================================

# Each piece is stored as [top, right, bottom, left].
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

def solve_puzzle_with_stats(pieces: List[List[int]], find_all_solutions: Optional[bool] = None):
    # Solve an nxn matched-squares puzzle using backtracking.
    if not pieces:
        return None

    count = len(pieces)
    n = int(round(math.sqrt(count)))
    if n * n != count:
        raise ValueError(f"The number of pieces ({count}) must form a perfect square grid")

    search_all = FIND_ALL_SOLUTIONS if find_all_solutions is None else find_all_solutions

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

    def backtrack(position: int) -> bool:
        nonlocal steps, solution_count, first_solution_grid
        steps += 1

        if position == count:
            solution_count += 1
            if solution_count == 1:
                first_solution_grid = [[board[row][col]["piece"] for col in range(n)] for row in range(n)]
            return True

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

                if search_all:
                    backtrack(position + 1)
                elif backtrack(position + 1):
                    return True

                used[piece_index] = False
                board[row][col] = None

        return False

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
    result = solve_puzzle_with_stats(pieces, find_all_solutions=False)
    return None if result is None or result["grid"] is None else result["grid"]

def parse_pieces_with_line_ranges(text: str) -> Tuple[List[List[int]], List[Tuple[int, int]]]:
    # Parse integers from the input while preserving the line range for each piece.
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [(index, line) for index, line in enumerate(lines, 1) if line]

    if not non_empty_lines:
        return [], []

    all_piece_lines = [re.findall(r"-?\d+", line) for _, line in non_empty_lines]
    if all(len(tokens) == 4 for tokens in all_piece_lines):
        pieces = [[int(token) for token in tokens] for tokens in all_piece_lines]
        line_ranges = [(line_no, line_no) for line_no, _ in non_empty_lines]
        return pieces, line_ranges

    tokens = re.findall(r"-?\d+", text)
    values = [int(token) for token in tokens]
    pieces = [values[i : i + 4] for i in range(0, len(values), 4)]
    if not pieces:
        return [], []
    return pieces, [(1, len(lines)) for _ in pieces]


def parse_pieces(text: str) -> List[List[int]]:
    pieces, _ = parse_pieces_with_line_ranges(text)
    return pieces

def print_solution(grid: List[List[List[int]]]) -> None:
    # Print the solved grid as one piece per line without blank lines.
    for row in grid:
        for piece in row:
            print(*piece)

def main() -> None:
    if SOLVE_MULTIPLE_PUZZLES:
        # Hide the main tkinter window
        root = tk.Tk()
        root.withdraw()
        filename = filedialog.askopenfilename(
            title="Open puzzle dataset",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        root.destroy()

        if not filename:
            print("No file selected. Exiting.")
            sys.exit(0)

        basename = os.path.basename(filename)
        # Assuming filename format like: scrambledPuzzles_4x4_100.txt
        match = re.search(r"_(\d+)x\1_(\d+)", basename)

        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()

        all_pieces, line_ranges = parse_pieces_with_line_ranges(text)

        if match:
            n = int(match.group(1))
            total_puzzles = int(match.group(2))
        else:
            # Fallback if the filename doesn't match the expected format
            print("Could not extract puzzle size and count from filename. Assuming 1 puzzle.")
            total_puzzles = 1
            n = int(math.sqrt(len(all_pieces)))

        expected_piece_count = n * n * total_puzzles
        if len(all_pieces) != expected_piece_count:
            print(f"Warning: Dataset has {len(all_pieces)} pieces, expected {expected_piece_count}.")
            # Adjust puzzle count based on actual pieces found
            total_puzzles = len(all_pieces) // (n * n)

        start_time_total = time.perf_counter()
        four_solution_lines: List[str] = []

        for idx in range(total_puzzles):
            start_index = idx * n * n
            end_index = start_index + n * n
            puzzle = all_pieces[start_index:end_index]
            if not puzzle:
                continue

            line_start = line_ranges[start_index][0] if start_index < len(line_ranges) else 1
            line_end = line_ranges[end_index - 1][1] if end_index <= len(line_ranges) else line_ranges[-1][1]
            result = solve_puzzle_with_stats(puzzle, find_all_solutions=FIND_ALL_SOLUTIONS)
            if result is not None:
                print(f"Puzzle {idx + 1}: {result['solution_count']:,} solution(s)")
                if result["solution_count"] == 4:
                    four_solution_lines.append(f"Lines {line_start}-{line_end}")
            else:
                print(f"Puzzle {idx + 1}: 0 solution(s)")

        elapsed_time_total = time.perf_counter() - start_time_total

        # Print overall stats exactly matching your layout style
        print(f"Puzzle size: {n}x{n}")
        print(f"Number of puzzles: {total_puzzles}")
        print(f"Total time elapsed: {elapsed_time_total:.4f} seconds")
        if total_puzzles > 0:
            print(f"Average time per puzzle: {elapsed_time_total / total_puzzles:.4f} seconds")

        if four_solution_lines:
            print("Puzzles with exactly 4 solutions:")
            print(", ".join(four_solution_lines))

    else:
        # Original single-puzzle behavior
        print("Input puzzle in row number form and press Enter twice:")
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
        result = solve_puzzle_with_stats(pieces, find_all_solutions=FIND_ALL_SOLUTIONS)

        if result and result["grid"] is not None:
            print(f"\nFound {result['solution_count']} solution(s).")
            print("First solution:")
            print_solution(result["grid"])
        else:
            print("\nNo solution exists for this configuration.")

if __name__ == "__main__":
    main()