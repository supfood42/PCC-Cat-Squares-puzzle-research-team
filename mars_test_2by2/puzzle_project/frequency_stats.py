import json
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
STATS_FILE = PROJECT_FOLDER / "frequency_stats.json"

# ============================================================
# SETTINGS
# ============================================================

# Record reusable local blocks from 2 x 2 through this size.
# 4 is a practical default. Larger exact blocks become sparse
# and can make the JSON file very large.
MAX_LOCAL_BLOCK_SIZE = 4

# Optionally also record one (n - 1) x (n - 1) block size.
# This is disabled by default because it usually provides little
# reusable information across unrelated puzzles.
RECORD_N_MINUS_ONE_BLOCKS = False

# Prevent any one table from growing without limit.
MAX_KEYS_PER_TABLE = 50_000

# Remove entries seen fewer than this many times when pruning.
MIN_COUNT_TO_KEEP = 2


# ============================================================
# BASIC STATISTICS STRUCTURE
# ============================================================

def empty_statistics() -> dict:
    """
    Create a blank statistics structure.
    """

    return {
        "schema_version": 2,
        "puzzles_recorded": 0,
        "solutions_recorded": 0,

        # Existing corner-frequency data.
        "corner_positions": {
            "board_corner": {},
            "board_edge": {},
            "interior": {},
        },

        # Fixed-orientation internal junctions.
        "junction_frequency": {},

        # Actual oriented piece edges by board category.
        "piece_position_frequency": {},

        # Given top and left neighbors, which oriented piece
        # appears most often?
        "neighbor_candidate_frequency": {},

        # Adjacent oriented-piece pairs.
        "horizontal_pair_frequency": {},
        "vertical_pair_frequency": {},

        # Exact fixed-orientation k x k blocks.
        # Stored as:
        # {
        #     "2": {...},
        #     "3": {...},
        #     "4": {...},
        # }
        "block_frequency": {},
    }


def _merge_missing_defaults(
    statistics: dict,
) -> dict:
    """
    Upgrade older JSON files by inserting any missing fields.
    Existing counts are preserved.
    """

    defaults = empty_statistics()

    for key, default_value in defaults.items():
        if key not in statistics:
            statistics[key] = default_value

    statistics.setdefault(
        "corner_positions",
        {},
    )

    for category in (
        "board_corner",
        "board_edge",
        "interior",
    ):
        statistics[
            "corner_positions"
        ].setdefault(
            category,
            {},
        )

    statistics.setdefault(
        "junction_frequency",
        {},
    )
    statistics.setdefault(
        "piece_position_frequency",
        {},
    )
    statistics.setdefault(
        "neighbor_candidate_frequency",
        {},
    )
    statistics.setdefault(
        "horizontal_pair_frequency",
        {},
    )
    statistics.setdefault(
        "vertical_pair_frequency",
        {},
    )
    statistics.setdefault(
        "block_frequency",
        {},
    )

    statistics["schema_version"] = 2

    return statistics


def load_statistics() -> dict:
    """
    Load existing statistics, or create blank statistics when
    the file does not yet exist.

    Older files are upgraded automatically.
    """

    if not STATS_FILE.exists():
        return empty_statistics()

    try:
        with STATS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            statistics = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return empty_statistics()

    if not isinstance(
        statistics,
        dict,
    ):
        return empty_statistics()

    return _merge_missing_defaults(
        statistics
    )


def save_statistics(
    statistics: dict,
) -> None:
    """
    Overwrite the saved statistics file.
    """

    statistics = _merge_missing_defaults(
        statistics
    )

    with STATS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            statistics,
            file,
            indent=2,
            sort_keys=True,
        )


# ============================================================
# GENERAL HELPERS
# ============================================================

def increment_dictionary_count(
    dictionary: dict,
    key,
    amount: int = 1,
) -> None:
    """
    Increment one JSON-compatible dictionary count.
    """

    string_key = str(key)

    dictionary[string_key] = (
        dictionary.get(
            string_key,
            0,
        )
        + amount
    )


def board_position_category(
    row: int,
    column: int,
    n: int,
) -> str:
    """
    Classify a board position as board_corner, board_edge,
    or interior.
    """

    on_top_or_bottom = (
        row == 0
        or row == n - 1
    )

    on_left_or_right = (
        column == 0
        or column == n - 1
    )

    if (
        on_top_or_bottom
        and on_left_or_right
    ):
        return "board_corner"

    if (
        on_top_or_bottom
        or on_left_or_right
    ):
        return "board_edge"

    return "interior"


def candidate_edges_tuple(
    candidate_key: tuple[int, int],
    candidates: dict,
) -> tuple[int, int, int, int]:
    """
    Return actual oriented edges:
        top, right, bottom, left
    """

    return tuple(
        candidates[
            candidate_key
        ]["edges"]
    )


def candidate_edges_key(
    candidate_key: tuple[int, int],
    candidates: dict,
) -> str:
    """
    Convert actual oriented edges into a stable JSON key.
    """

    return ",".join(
        str(edge)
        for edge in candidate_edges_tuple(
            candidate_key,
            candidates,
        )
    )


def junction_to_key(
    junction: tuple[int, int, int, int],
) -> str:
    """
    Convert one fixed-orientation junction into a JSON key.
    """

    return ",".join(
        str(value)
        for value in junction
    )


def prune_frequency_table(
    table: dict,
    max_keys: int = MAX_KEYS_PER_TABLE,
    minimum_count: int = MIN_COUNT_TO_KEEP,
) -> dict:
    """
    Limit a frequency table so the statistics file does not
    grow forever.

    High-frequency patterns are retained first.
    """

    if len(table) <= max_keys:
        return table

    surviving_items = [
        (
            key,
            count,
        )
        for key, count in table.items()
        if count >= minimum_count
    ]

    surviving_items.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return dict(
        surviving_items[:max_keys]
    )


# ============================================================
# EXISTING CORNER STATISTICS
# ============================================================

def record_piece_corners(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record all four corner IDs of every placed piece,
    grouped by board-position category.
    """

    for row in range(n):
        for column in range(n):
            position = (
                row * n
                + column
            )

            candidate_key = solution[
                position
            ]

            corners = candidates[
                candidate_key
            ]["corners"]

            category = (
                board_position_category(
                    row,
                    column,
                    n,
                )
            )

            category_counts = (
                statistics[
                    "corner_positions"
                ][category]
            )

            for corner_id in corners:
                increment_dictionary_count(
                    category_counts,
                    corner_id,
                )


# ============================================================
# FIXED-ORIENTATION JUNCTION STATISTICS
# ============================================================

def get_internal_junction(
    solution: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
) -> tuple[int, int, int, int]:
    """
    Return the four corners around an internal crossing.

    Arrangement:

        A B
        C D

    Returned in this fixed clockwise order:

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

    a_corners = candidates[
        a_key
    ]["corners"]

    b_corners = candidates[
        b_key
    ]["corners"]

    c_corners = candidates[
        c_key
    ]["corners"]

    d_corners = candidates[
        d_key
    ]["corners"]

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
    Compatibility helper retained for older imports.

    Rotations are no longer merged. The fixed orientation is
    returned unchanged.
    """

    return junction


def record_junctions(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record every fixed-orientation internal 2 x 2 crossing.
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

            key = junction_to_key(
                junction
            )

            increment_dictionary_count(
                statistics[
                    "junction_frequency"
                ],
                key,
            )


# ============================================================
# PIECE POSITION AND NEIGHBOR LEARNING
# ============================================================

def record_piece_positions(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record actual oriented piece edges by board category.
    """

    table = statistics[
        "piece_position_frequency"
    ]

    for row in range(n):
        for column in range(n):
            position = (
                row * n
                + column
            )

            candidate_key = solution[
                position
            ]

            category = (
                board_position_category(
                    row,
                    column,
                    n,
                )
            )

            edges_key = candidate_edges_key(
                candidate_key,
                candidates,
            )

            key = (
                f"{category}|"
                f"{edges_key}"
            )

            increment_dictionary_count(
                table,
                key,
            )


def record_neighbor_candidates(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record:

        top neighbor
        left neighbor
        successful candidate

    Actual oriented edges are used so the statistics remain
    meaningful across different puzzles.
    """

    table = statistics[
        "neighbor_candidate_frequency"
    ]

    for row in range(n):
        for column in range(n):
            position = (
                row * n
                + column
            )

            candidate_key = solution[
                position
            ]

            candidate_value = (
                candidate_edges_key(
                    candidate_key,
                    candidates,
                )
            )

            if row > 0:
                top_key = solution[
                    (row - 1) * n
                    + column
                ]

                top_value = (
                    candidate_edges_key(
                        top_key,
                        candidates,
                    )
                )
            else:
                top_value = "BOUNDARY"

            if column > 0:
                left_key = solution[
                    row * n
                    + column - 1
                ]

                left_value = (
                    candidate_edges_key(
                        left_key,
                        candidates,
                    )
                )
            else:
                left_value = "BOUNDARY"

            key = (
                f"top={top_value}|"
                f"left={left_value}|"
                f"candidate={candidate_value}"
            )

            increment_dictionary_count(
                table,
                key,
            )


def record_adjacent_pairs(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record horizontal and vertical oriented-piece pairs.
    """

    horizontal_table = statistics[
        "horizontal_pair_frequency"
    ]

    vertical_table = statistics[
        "vertical_pair_frequency"
    ]

    for row in range(n):
        for column in range(n - 1):
            left_key = solution[
                row * n
                + column
            ]

            right_key = solution[
                row * n
                + column + 1
            ]

            key = (
                f"{candidate_edges_key(left_key, candidates)}"
                f"|"
                f"{candidate_edges_key(right_key, candidates)}"
            )

            increment_dictionary_count(
                horizontal_table,
                key,
            )

    for row in range(n - 1):
        for column in range(n):
            top_key = solution[
                row * n
                + column
            ]

            bottom_key = solution[
                (row + 1) * n
                + column
            ]

            key = (
                f"{candidate_edges_key(top_key, candidates)}"
                f"|"
                f"{candidate_edges_key(bottom_key, candidates)}"
            )

            increment_dictionary_count(
                vertical_table,
                key,
            )


# ============================================================
# MULTI-SCALE BLOCK LEARNING
# ============================================================

def extract_block_pattern(
    solution: list,
    start_row: int,
    start_column: int,
    block_size: int,
    n: int,
    candidates: dict,
) -> tuple[
    tuple[int, int, int, int],
    ...,
]:
    """
    Extract one fixed-orientation block in row-major order.
    """

    pattern = []

    for row in range(
        start_row,
        start_row + block_size,
    ):
        for column in range(
            start_column,
            start_column + block_size,
        ):
            position = (
                row * n
                + column
            )

            candidate_key = solution[
                position
            ]

            pattern.append(
                candidate_edges_tuple(
                    candidate_key,
                    candidates,
                )
            )

    return tuple(
        pattern
    )


def block_pattern_to_key(
    pattern: tuple[
        tuple[int, int, int, int],
        ...,
    ],
) -> str:
    """
    Convert a block into a compact JSON key.
    """

    return ";".join(
        ",".join(
            str(edge)
            for edge in piece_edges
        )
        for piece_edges in pattern
    )


def block_sizes_to_record(
    n: int,
) -> list[int]:
    """
    Choose practical reusable block sizes.

    By default this records 2 x 2, 3 x 3, and 4 x 4 when
    those sizes fit. An optional (n - 1) size can be enabled.
    """

    sizes = set()

    maximum_local_size = min(
        MAX_LOCAL_BLOCK_SIZE,
        n,
    )

    for block_size in range(
        2,
        maximum_local_size + 1,
    ):
        sizes.add(
            block_size
        )

    if (
        RECORD_N_MINUS_ONE_BLOCKS
        and n >= 3
    ):
        sizes.add(
            n - 1
        )

    return sorted(
        sizes
    )


def record_block_patterns(
    statistics: dict,
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Record fixed-orientation local block patterns.
    """

    block_frequency = statistics[
        "block_frequency"
    ]

    for block_size in block_sizes_to_record(
        n
    ):
        size_key = str(
            block_size
        )

        size_table = block_frequency.setdefault(
            size_key,
            {},
        )

        number_of_starts = (
            n
            - block_size
            + 1
        )

        for start_row in range(
            number_of_starts
        ):
            for start_column in range(
                number_of_starts
            ):
                pattern = extract_block_pattern(
                    solution=solution,
                    start_row=start_row,
                    start_column=start_column,
                    block_size=block_size,
                    n=n,
                    candidates=candidates,
                )

                key = block_pattern_to_key(
                    pattern
                )

                increment_dictionary_count(
                    size_table,
                    key,
                )

        block_frequency[
            size_key
        ] = prune_frequency_table(
            size_table
        )


# ============================================================
# RECORD ONE SOLUTION
# ============================================================

def record_solution_statistics(
    solution: list,
    n: int,
    candidates: dict,
) -> dict:
    """
    Load statistics, add one confirmed solution, prune large
    tables, save, and return the updated statistics.
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

    record_piece_positions(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    record_neighbor_candidates(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    record_adjacent_pairs(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    record_block_patterns(
        statistics=statistics,
        solution=solution,
        n=n,
        candidates=candidates,
    )

    statistics[
        "puzzles_recorded"
    ] += 1

    statistics[
        "solutions_recorded"
    ] += 1

    for table_name in (
        "junction_frequency",
        "piece_position_frequency",
        "neighbor_candidate_frequency",
        "horizontal_pair_frequency",
        "vertical_pair_frequency",
    ):
        statistics[
            table_name
        ] = prune_frequency_table(
            statistics[
                table_name
            ]
        )

    save_statistics(
        statistics
    )

    return statistics


# ============================================================
# SCORING HELPERS USED BY OTHER FILES
# ============================================================

def corner_position_score(
    corner_id: int,
    category: str,
    statistics: dict,
) -> float:
    """
    Return a smoothed corner-position priority score.
    """

    statistics = _merge_missing_defaults(
        statistics
    )

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
        total_count
        + number_of_corner_types
    )


def junction_frequency_score(
    junction: tuple[int, int, int, int],
    statistics: dict,
) -> int:
    """
    Return how often this exact oriented junction occurred.
    """

    statistics = _merge_missing_defaults(
        statistics
    )

    key = junction_to_key(
        junction
    )

    return statistics[
        "junction_frequency"
    ].get(
        key,
        0,
    )


# ============================================================
# READABLE REPORT
# ============================================================

def _append_top_entries(
    lines: list[str],
    title: str,
    table: dict,
    limit: int = 30,
) -> None:
    lines.extend([
        title,
        "-" * 75,
    ])

    sorted_items = sorted(
        table.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not sorted_items:
        lines.append(
            "(no data)"
        )
    else:
        for key, count in sorted_items[
            :limit
        ]:
            lines.append(
                f"{key}: {count}"
            )

    lines.append("")


def write_frequency_report(
    statistics: dict,
) -> Path:
    """
    Write a readable summary report.
    """

    statistics = _merge_missing_defaults(
        statistics
    )

    report_file = (
        PROJECT_FOLDER
        / "frequency_stats_report.txt"
    )

    lines = [
        "FREQUENCY STATISTICS REPORT",
        "=" * 75,
        "",
        (
            "Schema version: "
            f"{statistics['schema_version']}"
        ),
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
        _append_top_entries(
            lines=lines,
            title=(
                f"CORNER IDS AT "
                f"{category.upper()}"
            ),
            table=statistics[
                "corner_positions"
            ][category],
            limit=20,
        )

    _append_top_entries(
        lines=lines,
        title=(
            "MOST COMMON ORIENTED "
            "INTERNAL JUNCTIONS"
        ),
        table=statistics[
            "junction_frequency"
        ],
        limit=50,
    )

    _append_top_entries(
        lines=lines,
        title=(
            "MOST COMMON PIECES BY "
            "BOARD CATEGORY"
        ),
        table=statistics[
            "piece_position_frequency"
        ],
        limit=50,
    )

    _append_top_entries(
        lines=lines,
        title=(
            "MOST COMMON TOP/LEFT "
            "NEIGHBOR CANDIDATES"
        ),
        table=statistics[
            "neighbor_candidate_frequency"
        ],
        limit=50,
    )

    _append_top_entries(
        lines=lines,
        title="MOST COMMON HORIZONTAL PAIRS",
        table=statistics[
            "horizontal_pair_frequency"
        ],
        limit=50,
    )

    _append_top_entries(
        lines=lines,
        title="MOST COMMON VERTICAL PAIRS",
        table=statistics[
            "vertical_pair_frequency"
        ],
        limit=50,
    )

    for block_size in sorted(
        statistics[
            "block_frequency"
        ],
        key=lambda value: int(value),
    ):
        _append_top_entries(
            lines=lines,
            title=(
                f"MOST COMMON ORIENTED "
                f"{block_size} x {block_size} BLOCKS"
            ),
            table=statistics[
                "block_frequency"
            ][block_size],
            limit=20,
        )

    lines.extend([
        "=" * 75,
        "END OF REPORT",
        "",
    ])

    with report_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join(lines)
        )

    return report_file


# ============================================================
# RESET
# ============================================================

def clear_statistics() -> None:
    """
    Delete the saved learning statistics.
    """

    if STATS_FILE.exists():
        STATS_FILE.unlink()


if __name__ == "__main__":
    statistics = load_statistics()

    print(
        "Frequency statistics loaded."
    )
    print(
        "Puzzles recorded:",
        statistics[
            "puzzles_recorded"
        ],
    )
    print(
        "Solutions recorded:",
        statistics[
            "solutions_recorded"
        ],
    )