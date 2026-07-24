import math
import os
import random
import re
import sys
import time
import tkinter as tk
from tkinter import filedialog
from typing import List, Optional

import numpy as np

try:
    import cupy as cp
except Exception:  # pragma: no cover - optional dependency
    cp = None

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SOLVE_MULTIPLE_PUZZLES = True
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


def _get_backend():
    # Use CuPy when a CUDA device is available; otherwise fall back to NumPy.
    if cp is not None:
        try:
            if cp.cuda.runtime.getDeviceCount() > 0:
                return cp, "gpu"
        except Exception:
            pass
    return np, "cpu"


def _matches_gpu(left_vals, right_vals, xp):
    left_vals = xp.asarray(left_vals, dtype=xp.int32)
    right_vals = xp.asarray(right_vals, dtype=xp.int32)
    return (left_vals != 0) & (right_vals != 0) & (xp.abs(left_vals) == xp.abs(right_vals)) & (left_vals + right_vals == 0)


def matches(left: Optional[int], right: Optional[int]) -> bool:
    # Check whether two sides form a valid cat-head/cat-body match.
    return (
        left is not None
        and right is not None
        and abs(left) == abs(right)
        and left + right == 0
    )


def solve_puzzle_with_stats(pieces: List[List[int]]):
    # Solve the puzzle using a GPU-accelerated batch evaluation of candidate placements.
    if not pieces:
        return None

    count = len(pieces)
    n = int(round(math.sqrt(count)))
    if n * n != count:
        raise ValueError(f"The number of pieces ({count}) must form a perfect square grid")

    print("\n[Running] Initiating solver and mapping layers...")

    rotations = build_rotations(pieces)
    xp, backend = _get_backend()
    rotation_tensor = xp.asarray(
        [[rotation for rotation in piece_rotations] for piece_rotations in rotations],
        dtype=xp.int32,
    )

    board: List[List[Optional[dict]]] = [[None] * n for _ in range(n)]
    used = [False] * count
    start_time = time.perf_counter()
    placements_tried = 0
    solution_count = 0
    first_solution_grid: Optional[List[List[List[int]]]] = None
    rng = random.Random(0)

    def backtrack(position: int) -> bool:
        nonlocal placements_tried, solution_count, first_solution_grid

        if position == count:
            solution_count += 1
            if solution_count == 1:
                first_solution_grid = [[board[row][col]["piece"] for col in range(n)] for row in range(n)]
            return True

        row, col = divmod(position, n)
        available_piece_indices = [idx for idx in range(count) if not used[idx]]
        if not available_piece_indices:
            return False

        piece_ids = xp.asarray(available_piece_indices, dtype=xp.int32)
        piece_ids = xp.repeat(piece_ids, 4)
        rot_ids = xp.tile(xp.arange(4, dtype=xp.int32), len(available_piece_indices))
        candidate_values = rotation_tensor[piece_ids, rot_ids]

        valid_mask = xp.ones(candidate_values.shape[0], dtype=xp.bool_)
        if row > 0:
            above = board[row - 1][col]
            if above is not None:
                valid_mask &= _matches_gpu(candidate_values[:, 0], xp.asarray([above["piece"][2]], dtype=xp.int32), xp)
        if col > 0:
            left = board[row][col - 1]
            if left is not None:
                valid_mask &= _matches_gpu(candidate_values[:, 3], xp.asarray([left["piece"][1]], dtype=xp.int32), xp)

        valid_indices = xp.nonzero(valid_mask)[0]
        if backend == "gpu":
            valid_indices = valid_indices.get()
        else:
            valid_indices = valid_indices.tolist()

        if not valid_indices:
            return False

        candidate_order = list(valid_indices)
        rng.shuffle(candidate_order)

        for candidate_index in candidate_order:
            placements_tried += 1

            piece_index = int(piece_ids[candidate_index].item() if hasattr(piece_ids[candidate_index], "item") else piece_ids[candidate_index])
            rotation_index = int(rot_ids[candidate_index].item() if hasattr(rot_ids[candidate_index], "item") else rot_ids[candidate_index])
            rotated_piece = [int(value) for value in candidate_values[candidate_index].tolist()] if backend == "gpu" else [int(value) for value in candidate_values[candidate_index]]

            board[row][col] = {
                "piece": rotated_piece,
                "index": piece_index,
                "rotation": rotation_index,
            }
            used[piece_index] = True

            if backtrack(position + 1):
                return True

            used[piece_index] = False
            board[row][col] = None

        return False

    solved = backtrack(0)
    elapsed_seconds = time.perf_counter() - start_time

    print("\r" + " " * 50 + "\r", end="")
    print("[Done] Search finished.                           ")
    print(f"Backend: {backend.upper()}")
    print(f"Total placements tried: {placements_tried:,}")
    print(f"Time elapsed: {elapsed_seconds:.4f} seconds")
    print(f"Solutions found: {solution_count:,}")

    if not solved:
        return None

    solved_grid = [[board[row][col]["piece"] for col in range(n)] for row in range(n)]
    return {
        "grid": solved_grid,
        "placements_tried": placements_tried,
        "solution_count": solution_count,
        "elapsed_ms": elapsed_seconds * 1000.0,
    }


def solve_puzzle(pieces: List[List[int]]):
    # Convenience wrapper that returns the solved grid.
    result = solve_puzzle_with_stats(pieces)
    return None if result is None else result["grid"]


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
    if SOLVE_MULTIPLE_PUZZLES:
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
        match = re.search(r"_(\d+)x\1_(\d+)", basename)

        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()

        all_pieces = parse_pieces(text)

        if match:
            n = int(match.group(1))
            total_puzzles = int(match.group(2))
        else:
            print("Could not extract puzzle size and count from filename. Assuming 1 puzzle.")
            total_puzzles = 1
            n = int(math.sqrt(len(all_pieces)))

        expected_piece_count = n * n * total_puzzles
        if len(all_pieces) != expected_piece_count:
            print(f"Warning: Dataset has {len(all_pieces)} pieces, expected {expected_piece_count}.")
            total_puzzles = len(all_pieces) // (n * n)

        start_time_total = time.perf_counter()
        for idx in range(total_puzzles):
            puzzle = all_pieces[idx * n * n : (idx + 1) * n * n]
            solve_puzzle_with_stats(puzzle)

        elapsed_time_total = time.perf_counter() - start_time_total
        print(f"Puzzle size: {n}x{n}")
        print(f"Number of puzzles: {total_puzzles}")
        print(f"Total time elapsed: {elapsed_time_total:.4f} seconds")
        if total_puzzles > 0:
            print(f"Average time per puzzle: {elapsed_time_total / total_puzzles:.4f} seconds")

    else:
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
        result = solve_puzzle_with_stats(pieces)

        if result:
            print("\nSolved puzzle:")
            print_solution(result["grid"])
        else:
            print("\nNo solution exists for this configuration.")


if __name__ == "__main__":
    main()