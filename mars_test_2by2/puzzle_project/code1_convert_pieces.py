# code1_convert_pieces.py

VALUE_ORDER = [1, 2, 3, 4, -1, -2, -3, -4]

VALUE_TO_INDEX = {
    value: index
    for index, value in enumerate(VALUE_ORDER)
}


def pair_to_corner_id(first: int, second: int) -> int:
    """
    Convert an ordered pair [first, second]
    into a corner ID from 1 through 64.
    """

    if first not in VALUE_TO_INDEX or second not in VALUE_TO_INDEX:
        raise ValueError(
            f"Corner values must come from {VALUE_ORDER}."
        )

    return (
        VALUE_TO_INDEX[first] * 8
        + VALUE_TO_INDEX[second]
        + 1
    )


def corner_id_to_pair(corner_id: int) -> list[int]:
    """
    Convert a corner ID back into its ordered pair.
    """

    if not 1 <= corner_id <= 64:
        raise ValueError("Corner ID must be between 1 and 64.")

    position = corner_id - 1

    return [
        VALUE_ORDER[position // 8],
        VALUE_ORDER[position % 8],
    ]


def piece_to_corners(edges: list[int]) -> list[int]:
    """
    Input edge order:
        [top, right, bottom, left]

    Output corner order:
        [top-left, top-right, bottom-right, bottom-left]
    """

    if len(edges) != 4:
        raise ValueError(
            "Each puzzle piece must contain exactly four edges."
        )

    top, right, bottom, left = edges

    return [
        pair_to_corner_id(left, top),
        pair_to_corner_id(top, right),
        pair_to_corner_id(right, bottom),
        pair_to_corner_id(bottom, left),
    ]


def convert_pieces(edge_pieces: list[list[int]]) -> list[list[int]]:
    """
    Convert several original puzzle pieces into corner-ID arrays.
    """

    return [
        piece_to_corners(piece)
        for piece in edge_pieces
    ]


def parse_multiline_input(text: str) -> list[list[int]]:
    """
    Convert multiline text into original edge arrays.

    Each line:
        top right bottom left
    """

    pieces = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1
    ):
        line = line.strip()

        if not line:
            continue

        try:
            edges = [int(value) for value in line.split()]
        except ValueError as error:
            raise ValueError(
                f"Line {line_number} contains a non-integer value."
            ) from error

        if len(edges) != 4:
            raise ValueError(
                f"Line {line_number} must contain four values."
            )

        invalid_values = [
            value
            for value in edges
            if value not in VALUE_ORDER
        ]

        if invalid_values:
            raise ValueError(
                f"Line {line_number} contains invalid values: "
                f"{invalid_values}"
            )

        pieces.append(edges)

    return pieces


# This section runs only when Code 1 is opened directly.
# It does not run when Code 3 imports Code 1.
if __name__ == "__main__":
    print("Paste puzzle pieces.")
    print("Use: top right bottom left")
    print("Enter a blank line when finished.\n")

    lines = []

    while True:
        line = input()

        if not line.strip():
            break

        lines.append(line)

    original_pieces = parse_multiline_input("\n".join(lines))
    converted_pieces = convert_pieces(original_pieces)

    print("\nConverted corner arrays:")

    for number, corners in enumerate(
        converted_pieces,
        start=1
    ):
        print(f"Piece {number}: {corners}")