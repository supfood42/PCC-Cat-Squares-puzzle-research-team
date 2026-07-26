import json
from collections import Counter
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
STATS_FILE = PROJECT_FOLDER / "frequency_stats.json"


def empty_statistics() -> dict:
    """
    Create a blank statistics structure.
    """

    return {
        "puzzles_recorded": 0,
        "solutions_recorded": 0,
        "corner_positions": {
            "board_corner": {},
            "board_edge": {},
            "interior": {},
        },
        "junction_frequency": {},
    }


def load_statistics() -> dict:
    """
    Load existing statistics, or create blank statistics
    when the file does not yet exist.
    """

    if not STATS_FILE.exists():
        return empty_statistics()

    try:
        with STATS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return empty_statistics()


def save_statistics(statistics: dict) -> None:
    """
    Overwrite the saved statistics file.
    """

    with STATS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            statistics,
            file,
            indent=2,
            sort_keys=True,
        )


def board_position_category(
    row: int,
    column: int,
    n: int,
) -> str:
    """
    Classify a board position.

    board_corner:
        one of the four outside corner positions

    board_edge:
        outside boundary, but not a board corner

    interior:
        does not touch the outside boundary
    """

    on_top_or_bottom = (
        row == 0
        or row == n - 1
    )

    on_left_or_right = (
        column == 0
        or column == n - 1
    )

    if on_top_or_bottom and on_left_or_right:
        return "board_corner"

    if on_top_or_bottom or on_left_or_right:
        return "board_edge"

    return "interior"


def increment_dictionary_count(
    dictionary: dict,
    key,
    amount: int = 1,
) -> None:
    """
    JSON object keys must be strings.
    """

    string_key = str(key)

    dictionary[string_key] = (
        dictionary.get(string_key, 0)
        + amount
    )


def record_piece_corners(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record all four corner IDs of each placed piece,
    grouped by the piece's board-position category.
    """

    for row in range(n):
        for column in range(n):
            position = row * n + column
            candidate_key = solution[position]

            corners = candidates[
                candidate_key
            ]["corners"]

            category = board_position_category(
                row,
                column,
                n,
            )

            category_counts = statistics[
                "corner_positions"
            ][category]

            for corner_id in corners:
                increment_dictionary_count(
                    category_counts,
                    corner_id,
                )


def get_internal_junction(
    solution: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
) -> tuple[int, int, int, int]:
    """
    Return the corners around an internal crossing.

    Arrangement:

        A B
        C D

    Clockwise center corners:

        A bottom-right
        B bottom-left
        D top-left
        C top-right
    """

    a_key = solution[
        (row - 1) * n
        + (column - 1)
    ]

    b_key = solution[
        (row - 1) * n
        + column
    ]

    c_key = solution[
        row * n
        + (column - 1)
    ]

    d_key = solution[
        row * n
        + column
    ]

    a_corners = candidates[a_key]["corners"]
    b_corners = candidates[b_key]["corners"]
    c_corners = candidates[c_key]["corners"]
    d_corners = candidates[d_key]["corners"]

    return (
        a_corners[2],
        b_corners[3],
        d_corners[0],
        c_corners[1],
    )


def canonical_junction(
    junction: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """
    Treat whole-junction rotations as one frequency pattern.

    Reflections remain different.
    """

    rotations = [
        junction,
        (
            junction[3],
            junction[0],
            junction[1],
            junction[2],
        ),
        (
            junction[2],
            junction[3],
            junction[0],
            junction[1],
        ),
        (
            junction[1],
            junction[2],
            junction[3],
            junction[0],
        ),
    ]

    return min(rotations)


def junction_to_key(
    junction: tuple[int, int, int, int],
) -> str:
    """
    Convert a junction into a stable JSON key.
    """

    return ",".join(
        str(value)
        for value in junction
    )


def record_junctions(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record every internal 2 x 2 crossing.
    """

    for row in range(1, n):
        for column in range(1, n):
            junction = get_internal_junction(
                solution=solution,
                row=row,
                column=column,
                n=n,
                candidates=candidates,
            )

            canonical = canonical_junction(
                junction
            )

            key = junction_to_key(
                canonical
            )

            increment_dictionary_count(
                statistics[
                    "junction_frequency"
                ],
                key,
            )


def record_solution_statistics(
    solution: list,
    n: int,
    candidates: dict,
) -> dict:
    """
    Load the current statistics, add one confirmed solution,
    save the updated file, and return the statistics.
    """

    statistics = load_statistics()

    record_piece_corners(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    record_junctions(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    statistics["puzzles_recorded"] += 1
    statistics["solutions_recorded"] += 1

    save_statistics(statistics)

    return statistics


def corner_position_score(
    corner_id: int,
    category: str,
    statistics: dict,
) -> float:
    """
    Return a smoothed corner-position priority score.

    The +1 values prevent division by zero.
    """

    category_counts = statistics[
        "corner_positions"
    ][category]

    total_count = sum(
        category_counts.values()
    )

    corner_count = category_counts.get(
        str(corner_id),
        0,
    )

    number_of_corner_types = 64

    return (
        corner_count + 1
    ) / (
        total_count + number_of_corner_types
    )


def junction_frequency_score(
    junction: tuple[int, int, int, int],
    statistics: dict,
) -> int:
    """
    Return how often a junction has previously occurred.
    """

    canonical = canonical_junction(
        junction
    )

    key = junction_to_key(
        canonical
    )

    return statistics[
        "junction_frequency"
    ].get(key, 0)


def write_frequency_report(
    statistics: dict,
) -> Path:
    """
    Write a readable report.
    """

    report_file = (
        PROJECT_FOLDER
        / "frequency_stats_report.txt"
    )

    lines = [
        "FREQUENCY STATISTICS REPORT",
        "=" * 75,
        "",
        (
            "Puzzles recorded: "
            f"{statistics['puzzles_recorded']}"
        ),
        (
            "Solutions recorded: "
            f"{statistics['solutions_recorded']}"
        ),
        "",
    ]

    for category in (
        "board_corner",
        "board_edge",
        "interior",
    ):
        counts = statistics[
            "corner_positions"
        ][category]

        sorted_counts = sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        lines.extend([
            category.upper(),
            "-" * 75,
        ])

        for corner_id, count in sorted_counts[:20]:
            lines.append(
                f"Corner {corner_id}: {count}"
            )

        lines.append("")

    junction_counts = statistics[
        "junction_frequency"
    ]

    sorted_junctions = sorted(
        junction_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    lines.extend([
        "MOST COMMON INTERNAL JUNCTIONS",
        "-" * 75,
    ])

    for junction, count in sorted_junctions[:50]:
        lines.append(
            f"{junction}: {count}"
        )

    lines.extend([
        "",
        "=" * 75,
        "END OF REPORT",
        "",
    ])

    with report_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(lines))

    return report_file


def clear_statistics() -> None:
    """
    Delete the saved learning statistics.
    """

    if STATS_FILE.exists():
        STATS_FILE.unlink()