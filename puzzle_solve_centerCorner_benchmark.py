"""Compare center-corner solve times across multiple puzzle datasets."""

from __future__ import annotations

import math
import os
from pathlib import Path
import random
import re
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np


DATASET_PATTERN = re.compile(r"_(\d+)x\d+_(\d+)")


def rotate_piece(piece: list[int], times: int = 1) -> list[int]:
    rotated = list(piece)
    for _ in range(times % 4):
        rotated = [rotated[3], rotated[0], rotated[1], rotated[2]]
    return rotated


def build_rotations(pieces: list[list[int]]) -> list[list[list[int]]]:
    rotations = []
    for piece in pieces:
        options = []
        current = list(piece)
        for _ in range(4):
            options.append(current)
            current = rotate_piece(current)
        rotations.append(options)
    return rotations


def matches(left: Optional[int], right: Optional[int]) -> bool:
    return left is not None and right is not None and left + right == 0


def solve_puzzle(pieces: list[list[int]]) -> dict[str, float | bool | int]:
    """Solve one puzzle and return timing and search diagnostics."""
    count = len(pieces)
    n = math.isqrt(count)
    if n * n != count:
        raise ValueError(f"{count} pieces do not form a square board")

    rotations = build_rotations(pieces)
    board: list[list[Optional[dict]]] = [[None] * n for _ in range(n)]
    used = [False] * count
    states = 0
    rng = random.Random(0)
    start = time.perf_counter()

    def backtrack(position: int) -> bool:
        nonlocal states
        states += 1
        if position == count:
            return True

        row, col = divmod(position, n)
        piece_indices = list(range(count))
        rng.shuffle(piece_indices)
        rotation_indices = list(range(4))
        rng.shuffle(rotation_indices)

        for piece_index in piece_indices:
            if used[piece_index]:
                continue
            for rotation_index in rotation_indices:
                piece = rotations[piece_index][rotation_index]
                if row > 0 and not matches(piece[0], board[row - 1][col]["piece"][2]):
                    continue
                if col > 0 and not matches(piece[3], board[row][col - 1]["piece"][1]):
                    continue

                board[row][col] = {"piece": piece, "index": piece_index}
                used[piece_index] = True
                if backtrack(position + 1):
                    return True
                used[piece_index] = False
                board[row][col] = None
        return False

    solved = backtrack(0)
    elapsed = time.perf_counter() - start
    return {
        "solved": solved,
        "elapsed": elapsed,
        "states": states,
    }


def parse_dataset(path: str) -> tuple[int, int, list[list[list[int]]]]:
    """Read a dataset and return board size, puzzle count, and puzzle pieces."""
    text = Path(path).read_text(encoding="utf-8")
    values = [int(value) for value in re.findall(r"-?\d+", text)]
    match = DATASET_PATTERN.search(os.path.basename(path))

    if match:
        n = int(match.group(1))
        declared_count = int(match.group(2))
    else:
        n = math.isqrt(len(values) // 4)
        declared_count = 0

    pieces_per_puzzle = n * n * 4
    if n < 1 or len(values) % 4 != 0 or len(values) < pieces_per_puzzle:
        raise ValueError(f"Could not determine valid {n}x{n} puzzles in {path}")

    actual_count = len(values) // pieces_per_puzzle
    puzzle_count = actual_count if not declared_count else min(declared_count, actual_count)
    pieces = [
        [values[index : index + 4] for index in range(start, start + n * n * 4, 4)]
        for start in range(0, puzzle_count * pieces_per_puzzle, pieces_per_puzzle)
    ]
    return n, puzzle_count, pieces


def benchmark(paths: list[str]) -> list[dict]:
    results = []
    for path in paths:
        n, puzzle_count, puzzles = parse_dataset(path)
        times = []
        states = []
        solved_count = 0
        print(f"\nRunning {os.path.basename(path)} ({n}x{n}, {puzzle_count} puzzles)")
        for index, puzzle in enumerate(puzzles, start=1):
            result = solve_puzzle(puzzle)
            times.append(float(result["elapsed"]))
            states.append(int(result["states"]))
            solved_count += int(bool(result["solved"]))
            print(
                f"  Puzzle {index:>4}/{puzzle_count}: "
                f"{result['elapsed']:.6f} s, {result['states']:,} states"
            )

        results.append({
            "path": path,
            "label": f"{n}x{n}",
            "n": n,
            "count": puzzle_count,
            "times": times,
            "mean": float(np.mean(times)) if times else 0.0,
            "std": float(np.std(times, ddof=1)) if len(times) > 1 else 0.0,
            "median": float(np.median(times)) if times else 0.0,
            "states_mean": float(np.mean(states)) if states else 0.0,
            "solved": solved_count,
        })
    return results


def make_chart(results: list[dict]) -> Path:
    grouped: dict[int, list[float]] = {}
    for item in results:
        grouped.setdefault(item["n"], []).extend(item["times"])
    chart_results = [
        {
            "label": f"{n}x{n}",
            "count": len(times),
            "mean": float(np.mean(times)),
            "std": float(np.std(times, ddof=1)) if len(times) > 1 else 0.0,
        }
        for n, times in sorted(grouped.items())
    ]
    labels = [item["label"] for item in chart_results]
    means = np.array([item["mean"] for item in chart_results])
    errors = np.array([item["std"] for item in chart_results])
    output = Path(__file__).with_name("center_corner_solve_time_comparison.png")

    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(10.5, 6.5), dpi=130)
    figure.patch.set_facecolor("#f7f8f5")
    axis.set_facecolor("#f7f8f5")
    positions = np.arange(len(results))
    bars = axis.bar(
        positions,
        means,
        yerr=errors,
        capsize=7,
        color="#287c73",
        edgecolor="#164f4a",
        linewidth=1.0,
        error_kw={"ecolor": "#d05b3f", "elinewidth": 2, "capthick": 2},
    )

    for bar, item in zip(bars, chart_results):
        height = bar.get_height()
        offset = max(means.max() * 0.025, 1e-7)
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            height + errors[list(bars).index(bar)] + offset,
            f"{height:.4g} s\nn={item['count']}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#25383a",
        )

    axis.set_xticks(positions, labels)
    axis.set_xlabel("Puzzle size", fontsize=11, labelpad=10)
    axis.set_ylabel("Mean solve time per puzzle (seconds)", fontsize=11, labelpad=10)
    axis.set_title("Center-Corner Solver Performance", loc="left", fontsize=19, weight="bold", pad=18, color="#173b3a")
    axis.text(
        0,
        1.01,
        "Bars show mean time; orange whiskers show sample standard deviation",
        transform=axis.transAxes,
        fontsize=10,
        color="#667477",
    )
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#d8dfdc", linewidth=0.8)
    axis.grid(axis="x", visible=False)
    positive_means = means[means > 0]
    if len(positive_means) > 1 and positive_means.max() / positive_means.min() >= 100:
        axis.set_yscale("log")
        axis.set_ylabel("Mean solve time per puzzle (seconds, log scale)", fontsize=11, labelpad=10)
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight")
    return output


def print_summary(results: list[dict]) -> None:
    print("\nSummary")
    print("Size    Puzzles  Solved  Mean (s)    Std dev     Median (s)  Mean states")
    print("-----   -------  ------  ----------  ----------  ----------  -----------")
    for item in sorted(results, key=lambda result: (result["n"], result["path"])):
        print(
            f"{item['label']:<7} {item['count']:>7}  {item['solved']:>6}  "
            f"{item['mean']:>10.6g}  {item['std']:>10.6g}  "
            f"{item['median']:>10.6g}  {item['states_mean']:>11,.1f}"
        )


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    paths = list(filedialog.askopenfilenames(
        parent=root,
        title="Select puzzle datasets to compare",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    ))
    root.destroy()
    if not paths:
        return

    try:
        results = benchmark(paths)
        output = make_chart(results)
        print_summary(results)
        print(f"\nChart saved to: {output}")
        print("Close the chart window to finish.")
        plt.show()
    except Exception as error:
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("Benchmark failed", str(error), parent=error_root)
        error_root.destroy()
        raise


if __name__ == "__main__":
    main()
