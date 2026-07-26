from collections import Counter
from math import isqrt


ALLOWED_VALUES = {
    1, 2, 3, 4,
    -1, -2, -3, -4,
}


def parse_piece_text(text: str) -> list[list[int]]:
    """
    Read raw puzzle pieces.

    Each nonempty line must contain:
        top right bottom left
    """

    pieces = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        line = line.strip()

        if not line:
            continue

        try:
            values = [
                int(value)
                for value in line.split()
            ]
        except ValueError as error:
            raise ValueError(
                f"Line {line_number} contains "
                f"a non-integer value."
            ) from error

        if len(values) != 4:
            raise ValueError(
                f"Line {line_number} must contain "
                f"exactly four values."
            )

        invalid_values = [
            value
            for value in values
            if value not in ALLOWED_VALUES
        ]

        if invalid_values:
            raise ValueError(
                f"Line {line_number} contains invalid "
                f"values: {invalid_values}"
            )

        pieces.append(values)

    return pieces


def determine_board_size(
    number_of_pieces: int
) -> int:
    """
    Determine n for an n × n puzzle.
    """

    n = isqrt(number_of_pieces)

    if n * n != number_of_pieces:
        raise ValueError(
            f"{number_of_pieces} pieces cannot form "
            f"a square n × n puzzle."
        )

    return n


def count_symbols(
    pieces: list[list[int]]
) -> Counter:
    """
    Count every signed edge value.
    """

    return Counter(
        edge
        for piece in pieces
        for edge in piece
    )


def calculate_discrepancy(
    symbol_counts: Counter
) -> dict[int, int]:
    """
    For each color:

        discrepancy =
        number of heads - number of bodies

    Positive values indicate excess heads.
    Negative values indicate excess bodies.
    """

    return {
        color: (
            symbol_counts[color]
            - symbol_counts[-color]
        )
        for color in range(1, 5)
    }


def minimum_boundary_edges(
    discrepancy: dict[int, int]
) -> int:
    """
    Calculate the minimum number of boundary edges
    required to hold the unmatched symbols.
    """

    return sum(
        abs(value)
        for value in discrepancy.values()
    )


def boundary_parity_is_possible(
    symbol_counts: Counter,
    n: int,
) -> bool:
    """
    Check whether boundary color counts can satisfy
    the required parity.

    Internal matches consume two edges of a color.
    Therefore, the number of boundary edges of each
    color must have the same odd/even parity as the
    total number of edges of that color.
    """

    required_minimum = 0

    for color in range(1, 5):
        heads = symbol_counts[color]
        bodies = symbol_counts[-color]

        total_color_edges = heads + bodies
        difference = abs(heads - bodies)

        boundary_count = difference

        if boundary_count % 2 != total_color_edges % 2:
            boundary_count += 1

        required_minimum += boundary_count

    return required_minimum <= 4 * n


def run_global_checks(
    pieces: list[list[int]]
) -> dict:
    """
    Run guaranteed preliminary checks.

    Passing these checks does not prove that the
    puzzle has a solution.

    Failing one of them proves that the puzzle
    cannot have a solution.
    """

    if not pieces:
        return {
            "possible": False,
            "reason": "No pieces were entered.",
        }

    try:
        n = determine_board_size(len(pieces))
    except ValueError as error:
        return {
            "possible": False,
            "reason": str(error),
        }

    symbol_counts = count_symbols(pieces)
    discrepancy = calculate_discrepancy(
        symbol_counts
    )

    required_boundary = minimum_boundary_edges(
        discrepancy
    )

    available_boundary = 4 * n

    if required_boundary > available_boundary:
        return {
            "possible": False,
            "reason": (
                "The head-body discrepancy requires "
                f"at least {required_boundary} boundary "
                f"edges, but an {n} × {n} puzzle has "
                f"only {available_boundary}."
            ),
            "n": n,
            "symbol_counts": symbol_counts,
            "discrepancy": discrepancy,
            "minimum_boundary_edges": required_boundary,
            "available_boundary_edges": available_boundary,
        }

    if not boundary_parity_is_possible(
        symbol_counts,
        n,
    ):
        return {
            "possible": False,
            "reason": (
                "The color totals and boundary size "
                "have incompatible odd/even parity."
            ),
            "n": n,
            "symbol_counts": symbol_counts,
            "discrepancy": discrepancy,
            "minimum_boundary_edges": required_boundary,
            "available_boundary_edges": available_boundary,
        }

    return {
        "possible": True,
        "reason": (
            "The puzzle passed the preliminary "
            "global checks."
        ),
        "n": n,
        "symbol_counts": symbol_counts,
        "discrepancy": discrepancy,
        "minimum_boundary_edges": required_boundary,
        "available_boundary_edges": available_boundary,
    }


def print_check_results(result: dict) -> None:
    """
    Display the check results clearly.
    """

    print("\n" + "=" * 55)

    if result["possible"]:
        print("GLOBAL CHECKS PASSED")
    else:
        print("NO SOLUTION")

    print("-" * 55)
    print(result["reason"])

    if "n" not in result:
        return

    print(
        f"\nBoard size: "
        f"{result['n']} × {result['n']}"
    )

    print(
        f"Minimum required boundary edges: "
        f"{result['minimum_boundary_edges']}"
    )

    print(
        f"Available boundary edges: "
        f"{result['available_boundary_edges']}"
    )

    print("\nHead-body discrepancies:")

    color_names = {
        1: "Yellow",
        2: "Pink",
        3: "Purple",
        4: "Green",
    }

    for color in range(1, 5):
        difference = result["discrepancy"][color]

        if difference > 0:
            description = (
                f"{difference} excess head(s)"
            )
        elif difference < 0:
            description = (
                f"{abs(difference)} excess body/bodies"
            )
        else:
            description = "balanced"

        print(
            f"  {color_names[color]}: "
            f"{description}"
        )


def main() -> None:
    print("Paste all puzzle pieces.")
    print("Use one piece per line:")
    print("top right bottom left")
    print()
    print(
        "Press Enter on a blank line "
        "when finished."
    )
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

    result = run_global_checks(pieces)
    print_check_results(result)


if __name__ == "__main__":
    main()