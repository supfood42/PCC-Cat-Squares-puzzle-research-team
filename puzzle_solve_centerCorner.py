import math
import random
import re
import sys
import time
from typing import List, Optional

# Each piece is stored as [top, right, bottom, left].
# A positive value means one cat side and a negative value means the opposite side;
# the absolute value is the color number (1..4).


def rotate_piece(piece: List[int], times: int = 1) -> List[int]:
    """Rotate a piece clockwise by the requested number of quarter turns."""
    rotated = list(piece)
    for _ in range(times % 4):
        rotated = [rotated[3], rotated[0], rotated[1], rotated[2]]
    return rotated


def build_rotations(pieces: List[List[int]]) -> List[List[List[int]]]:
    """Return every rotation for every piece."""
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
    """Check whether two sides form a valid cat-head/cat-body match."""
    return (
        left is not None
        and right is not None
        and abs(left) == abs(right)
        and left + right == 0
    )


def solve_puzzle_with_stats(pieces: List[List[int]]):
    """Solve an nxn matched-squares puzzle using backtracking."""
    if not pieces:
        return None

    count = len(pieces)
    n = int(round(math.sqrt(count)))
    if n * n != count:
        raise ValueError("The number of pieces must form a perfect square grid")

    rotations = build_rotations(pieces)
    board: List[List[Optional[dict]]] = [[None] * n for _ in range(n)]
    used = [False] * count
    start_time = time.perf_counter()
    steps = 0
    rng = random.Random(0)

    def backtrack(position: int) -> bool:
        nonlocal steps
        steps += 1

        if position == count:
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

                if backtrack(position + 1):
                    return True

                used[piece_index] = False
                board[row][col] = None

        return False

    solved = backtrack(0)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    if not solved:
        return None

    solved_grid = [[board[row][col]["piece"] for col in range(n)] for row in range(n)]
    return {
        "grid": solved_grid,
        "steps": steps,
        "elapsed_ms": elapsed_ms,
    }


def solve_puzzle(pieces: List[List[int]]):
    """Convenience wrapper that returns only the solved grid."""
    result = solve_puzzle_with_stats(pieces)
    return None if result is None else result["grid"]


def parse_pieces(text: str) -> List[List[int]]:
    """Parse all integers from the input and group them into four-value pieces."""
    tokens = re.findall(r"-?\d+", text)
    if not tokens:
        return []

    values = [int(token) for token in tokens]
    if len(values) % 4 != 0:
        raise ValueError("Each piece must contain exactly four values")

    pieces = []
    for i in range(0, len(values), 4):
        pieces.append(values[i : i + 4])
    return pieces


def print_solution(grid: List[List[List[int]]]) -> None:
    """Print the solved grid as one piece per line."""
    for row in grid:
        for piece in row:
            print(*piece)
        print()


def main() -> None:
    print("Enter the puzzle pieces as numbers, one piece per line or separated by spaces.")
    print("Press Ctrl+Z (Windows) or Ctrl+D (Linux/macOS) when finished.")
    text = sys.stdin.read().strip()
    if not text and len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    if not text:
        print("No puzzle input provided.")
        return

    try:
        pieces = parse_pieces(text)
    except ValueError as exc:
        print(exc)
        return

    result = solve_puzzle_with_stats(pieces)

    if result is None:
        print("No solution exists for the supplied pieces.")
        return

    print("Solved puzzle:")
    print_solution(result["grid"])
    print(f"Steps used: {result['steps']}")
    print(f"Time used: {result['elapsed_ms']:.2f} ms")


if __name__ == "__main__":
    main()