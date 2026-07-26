from collections import Counter

from frequency_stats import (
    board_position_category,
    canonical_junction,
    junction_frequency_score,
    load_statistics,
)


COLOR_NAMES = {
    1: "yellow",
    2: "pink",
    3: "purple",
    4: "green",
}


def calculate_symbol_discrepancy(
    pieces: list[list[int]],
) -> dict[int, int]:
    """
    Calculate heads minus bodies for each color.

    Positive:
        excess heads

    Negative:
        excess bodies
    """

    counts = Counter(
        edge
        for piece in pieces
        for edge in piece
    )

    return {
        color: counts[color] - counts[-color]
        for color in range(1, 5)
    }


def is_boundary_position(
    row: int,
    column: int,
    n: int,
) -> bool:
    """
    Return True when the position touches the outside
    boundary of the board.
    """

    return (
        row == 0
        or row == n - 1
        or column == 0
        or column == n - 1
    )


def outward_edge_indexes(
    row: int,
    column: int,
    n: int,
) -> list[int]:
    """
    Return which edge indexes face outside the board.

    Edge order:
        0 = top
        1 = right
        2 = bottom
        3 = left
    """

    indexes = []

    if row == 0:
        indexes.append(0)

    if column == n - 1:
        indexes.append(1)

    if row == n - 1:
        indexes.append(2)

    if column == 0:
        indexes.append(3)

    return indexes


def inward_edge_indexes(
    row: int,
    column: int,
    n: int,
) -> list[int]:
    """
    Return which edge indexes point toward another
    puzzle position.
    """

    outward = set(
        outward_edge_indexes(
            row,
            column,
            n,
        )
    )

    return [
        index
        for index in range(4)
        if index not in outward
    ]


def edge_imbalance_score(
    edge: int,
    discrepancy: dict[int, int],
) -> float:
    """
    Score one edge according to the global imbalance.

    Example:

        pink discrepancy = +4

    means pink heads are in excess.

    Therefore:
        pink head  2 receives a positive score
        pink body -2 receives a negative score
    """

    color = abs(edge)
    imbalance = discrepancy[color]

    if edge > 0:
        return float(imbalance)

    return float(-imbalance)


def boundary_rotation_score(
    candidate_key: tuple[int, int],
    row: int,
    column: int,
    n: int,
    candidates: dict,
    discrepancy: dict[int, int],
) -> float:
    """
    Score one piece rotation at one board position.

    Excess symbols receive positive scores when facing
    outside.

    Excess symbols receive penalties when facing inward.
    """

    edges = candidates[
        candidate_key
    ]["edges"]

    outward_indexes = outward_edge_indexes(
        row,
        column,
        n,
    )

    inward_indexes = inward_edge_indexes(
        row,
        column,
        n,
    )

    score = 0.0

    # Strong reward for useful outward edges.
    for edge_index in outward_indexes:
        edge = edges[edge_index]

        score += (
            2.0
            * edge_imbalance_score(
                edge,
                discrepancy,
            )
        )

    # Smaller penalty when excess symbols point inward.
    for edge_index in inward_indexes:
        edge = edges[edge_index]

        edge_score = edge_imbalance_score(
            edge,
            discrepancy,
        )

        if edge_score > 0:
            score -= 0.5 * edge_score

    return score


def position_type_score(
    candidate_key: tuple[int, int],
    row: int,
    column: int,
    n: int,
    candidates: dict,
    discrepancy: dict[int, int],
) -> float:
    """
    Give additional preference to pieces containing excess
    symbols when the position is on the boundary.

    This measures the piece generally, while
    boundary_rotation_score measures the exact rotation.
    """

    edges = candidates[
        candidate_key
    ]["edges"]

    total_excess_strength = 0.0

    for edge in edges:
        score = edge_imbalance_score(
            edge,
            discrepancy,
        )

        if score > 0:
            total_excess_strength += score

    if is_boundary_position(
        row,
        column,
        n,
    ):
        return 0.25 * total_excess_strength

    return -0.25 * total_excess_strength


def corner_frequency_score(
    candidate_key: tuple[int, int],
    row: int,
    column: int,
    n: int,
    candidates: dict,
    statistics: dict,
) -> float:
    """
    Score the candidate's corner IDs according to how often
    they appeared in this type of board position.

    This is a heuristic only.
    """

    if statistics["solutions_recorded"] == 0:
        return 0.0

    category = board_position_category(
        row,
        column,
        n,
    )

    category_counts = statistics[
        "corner_positions"
    ][category]

    total_count = sum(
        category_counts.values()
    )

    if total_count == 0:
        return 0.0

    corners = candidates[
        candidate_key
    ]["corners"]

    score = 0.0

    for corner_id in corners:
        corner_count = category_counts.get(
            str(corner_id),
            0,
        )

        score += (
            corner_count + 1
        ) / (
            total_count + 64
        )

    return score

def combined_candidate_score(
    candidate_key: tuple[int, int],
    row: int,
    column: int,
    n: int,
    candidates: dict,
    discrepancy: dict[int, int],
    statistics: dict,
) -> float:
    """
    Combine boundary and learned corner-position evidence.

    The values affect candidate order only.
    """

    boundary_score = boundary_rotation_score(
        candidate_key=candidate_key,
        row=row,
        column=column,
        n=n,
        candidates=candidates,
        discrepancy=discrepancy,
    )

    piece_position_score = position_type_score(
        candidate_key=candidate_key,
        row=row,
        column=column,
        n=n,
        candidates=candidates,
        discrepancy=discrepancy,
    )

    learned_corner_score = corner_frequency_score(
        candidate_key=candidate_key,
        row=row,
        column=column,
        n=n,
        candidates=candidates,
        statistics=statistics,
    )

    return (
        boundary_score
        + piece_position_score
        + 5.0 * learned_corner_score
    )

def sort_candidates_by_score(
    candidate_keys: list[tuple[int, int]],
    row: int,
    column: int,
    n: int,
    candidates: dict,
    discrepancy: dict[int, int],
    statistics: dict,
) -> list[tuple[int, int]]:
    """
    Sort candidates from highest heuristic priority to lowest.
    """

    return sorted(
        candidate_keys,
        key=lambda candidate_key: (
            combined_candidate_score(
                candidate_key=candidate_key,
                row=row,
                column=column,
                n=n,
                candidates=candidates,
                discrepancy=discrepancy,
                statistics=statistics,
            ),
            -candidate_key[0],
            -candidate_key[1],
        ),
        reverse=True,
    )

def describe_discrepancy(
    discrepancy: dict[int, int],
) -> list[str]:
    """
    Return readable descriptions for reports.
    """

    descriptions = []

    for color in range(1, 5):
        difference = discrepancy[color]
        name = COLOR_NAMES[color]

        if difference > 0:
            text = (
                f"{name}: {difference} excess head(s)"
            )

        elif difference < 0:
            text = (
                f"{name}: {abs(difference)} "
                f"excess body/bodies"
            )

        else:
            text = f"{name}: balanced"

        descriptions.append(text)

    return descriptions