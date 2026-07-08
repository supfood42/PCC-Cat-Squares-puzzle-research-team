import random

# Format: [top, right, bottom, left] as signed numbers
# Positive = head, negative = body; 1=green, 2=red, 3=purple, 4=yellow

def encode_side(side):
    """Convert a letter side to a signed number."""
    if side is None:
        return None
    color = {'g': 1, 'r': 2, 'p': 3, 'y': 4}[side.lower()]
    return color if side.islower() else -color


def opposite_side(side):
    """Return the opposite side with flipped sign."""
    return -side if side is not None else None

def rotate_piece(piece, times=1):
    """Rotate piece clockwise: [T,R,B,L] -> [L,T,R,B]"""
    for _ in range(times % 4):
        piece = [piece[3], piece[0], piece[1], piece[2]]
    return piece

def random_side():
    """Generate a random encoded side."""
    return encode_side(random.choice('RrPpYyGg'))


def generate_puzzle(n):
    """Generate solvable nxn puzzle starting from random center piece"""
    grid = [[None]*n for _ in range(n)]
    
    # Random center piece [top, right, bottom, left]
    center = [random_side() for _ in range(4)]
    mid = n // 2
    grid[mid][mid] = center
    
    # Generate clockwise spiral positions from center
    positions = get_spiral_positions(n, mid, mid)
    
    for r, c in positions:
        piece = generate_valid_piece(grid, r, c, n)
        grid[r][c] = piece
    
    return grid

def get_spiral_positions(n, start_r, start_c):
    """Generate clockwise spiral positions from center"""
    positions = []
    visited = {(start_r, start_c)}
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
    dr, dc = 0, 1
    steps_in_direction = 1
    
    r, c = start_r, start_c
    while len(visited) < n * n:
        for _ in range(2):  # Two sides per layer
            for _ in range(steps_in_direction):
                r, c = r + dr, c + dc
                if 0 <= r < n and 0 <= c < n and (r, c) not in visited:
                    positions.append((r, c))
                    visited.add((r, c))
            dr, dc = -dc, dr  # Rotate 90 degrees clockwise
        steps_in_direction += 1
    
    return positions

def generate_valid_piece(grid, row, col, n):
    """Generate a piece that matches all adjacent pieces"""
    piece = [None, None, None, None]  # [T, R, B, L]
    
    if row > 0 and grid[row-1][col]:  # Top neighbor
        piece[0] = opposite_side(grid[row-1][col][2])
    if col < n-1 and grid[row][col+1]:  # Right neighbor
        piece[1] = opposite_side(grid[row][col+1][3])
    if row < n-1 and grid[row+1][col]:  # Bottom neighbor
        piece[2] = opposite_side(grid[row+1][col][0])
    if col > 0 and grid[row][col-1]:  # Left neighbor
        piece[3] = opposite_side(grid[row][col-1][1])
    
    # Fill unconstrained sides with random colors
    for i in range(4):
        if piece[i] is None:
            piece[i] = random_side()
    
    return piece

def scramble_puzzle(grid, n):
    """Scramble by shuffling positions and random rotations"""
    flat = [piece for row in grid for piece in row]
    random.shuffle(flat)
    
    # Apply random rotations
    flat = [rotate_piece(piece.copy(), random.randint(0, 3)) for piece in flat]
    
    return [flat[i*n:(i+1)*n] for i in range(n)]


def print_pieces(grid):
    """Print each piece on its own line as four numbers."""
    for row in grid:
        for piece in row:
            print(*piece)


def collect_pieces(grid):
    """Return all pieces as rows of four numbers."""
    rows = []
    for row in grid:
        for piece in row:
            rows.append(piece)
    return rows


# Generate and output
n = int(input("Enter puzzle size (n for nxn): "))
total_puzzles = int(input("Enter total number of scrambled puzzles: "))

output_lines = []
for _ in range(total_puzzles):
    solved = generate_puzzle(n)
    scrambled = scramble_puzzle([row[:] for row in solved], n)
    for piece in collect_pieces(scrambled):
        output_lines.append(" ".join(map(str, piece)))

with open(f"scrambled_puzzles_{n}x{n}.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Saved {total_puzzles} scrambled puzzles to scrambled_puzzles_{n}x{n}.txt")