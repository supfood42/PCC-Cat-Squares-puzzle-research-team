import random

# Format: [top, right, bottom, left], lowercase=head, uppercase=body
# Colors: Y/y=yellow, R/r=red, P/p=purple, G/g=green

def opposite_side(side):
    """Convert a side to its opposite (e.g., top->bottom, right->left)"""
    return side.swapcase() if side else None

def can_connect(side1, side2):
    """Check if two sides can connect (same color and opposite case)"""
    return side1.lower() == side2.lower() and side1 != side2

def rotate_piece(piece, times=1):
    """Rotate piece clockwise: [T,R,B,L] -> [L,T,R,B]"""
    for _ in range(times % 4):
        piece = [piece[3], piece[0], piece[1], piece[2]]
    return piece

def generate_puzzle(n):
    """Generate solvable nxn puzzle starting from random center piece"""
    grid = [[None]*n for _ in range(n)]
    
    # Random center piece [top, right, bottom, left]
    center = [random.choice('Rr'), random.choice('Rr'), random.choice('Rr'), random.choice('Rr')]
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
    colors = 'RrPpYyGg'
    for i in range(4):
        if piece[i] is None:
            piece[i] = random.choice(colors)
    
    return piece

def scramble_puzzle(grid, n):
    """Scramble by shuffling positions and random rotations"""
    flat = [piece for row in grid for piece in row]
    random.shuffle(flat)
    
    # Apply random rotations
    flat = [rotate_piece(piece.copy(), random.randint(0, 3)) for piece in flat]
    
    return [flat[i*n:(i+1)*n] for i in range(n)]

# Generate and output
n = int(input("Enter puzzle size (n for nxn): "))
solved = generate_puzzle(n)
print(f"\nSolved {n}x{n} Puzzle:")
for row in solved:
    print(row)

scrambled = scramble_puzzle([row[:] for row in solved], n)
print(f"\nScrambled {n}x{n} Puzzle:")
for row in scrambled:
    print(row)