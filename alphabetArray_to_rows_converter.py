# Map colors to numbers
COLOR_MAP = {
    "g": 1,
    "green": 1,
    "r": 2,
    "red": 2,
    "p": 3,
    "purple": 3,
    "y": 4,
    "yellow": 4,
}


def decode_side(side):
    """Convert one side from letters to a signed number."""
    if isinstance(side, int):
        return side

    s = str(side).strip()
    if not s:
        raise ValueError("Empty side value")

    # Lowercase = head (+), uppercase = body (-)
    sign = 1 if s.islower() else -1
    color = s.lower()

    if color not in COLOR_MAP:
        raise ValueError(f"Unsupported color: {side}")
    return sign * COLOR_MAP[color]


def _collect_pieces(data):
    """Flatten nested lists into a list of pieces."""
    if not data:
        return []
    if isinstance(data, (str, int)):
        return [list(str(data))]
    if all(not isinstance(x, (list, tuple)) for x in data):
        return [list(data)]

    pieces = []
    for item in data:
        pieces.extend(_collect_pieces(item))
    return pieces


def alphabet_array_to_rows(alphabet_array):
    """Convert alphabet-style pieces to rows of numeric values."""
    pieces = _collect_pieces(alphabet_array)
    return [[decode_side(ch) for ch in piece] for piece in pieces]


if __name__ == "__main__":
    sample = [
        [
            ['R', 'G', 'G', 'G'],
            ['R', 'R', 'r', 'R'],
            ['R', 'P', 'g', 'R'],
            ['g', 'P', 'P', 'G'],
        ],
        [
            ['p', 'P', 'R', 'p'],
            ['P', 'G', 'r', 'g'],
            ['g', 'p', 'P', 'Y'],
            ['Y', 'Y', 'r', 'g'],
        ],
        [
            ['G', 'r', 'r', 'g'],
            ['y', 'P', 'R', 'G'],
            ['p', 'G', 'P', 'g'],
            ['G', 'g', 'r', 'g'],
        ],
        [
            ['r', 'p', 'p', 'g'],
            ['y', 'r', 'P', 'p'],
            ['g', 'G', 'p', 'r'],
            ['p', 'Y', 'y', 'Y'],
        ],
    ]

    print(alphabet_array_to_rows(sample))
