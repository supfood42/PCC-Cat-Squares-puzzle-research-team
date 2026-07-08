import random

# Format: [top, right, bottom, left], lowercase=head, uppercase=body
# Colors: Y/y=yellow, R/r=red, P/p=purple, B/b=blue, G/g=green

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

def generate_puzzle():
    """Generate solvable 3x3 puzzle starting from random center piece"""
    grid = [[None]*3 for _ in range(3)]
    used = set()
    
    # Random center piece [top, right, bottom, left]
    center = [random.choice('Rr'), random.choice('Rr'), random.choice('Rr'), random.choice('Rr')]
    grid[1][1] = center
    used.add(tuple(center))
    
    # Clockwise order from center: right, bottom-right, bottom, bottom-left, left, top-left, top, top-right
    positions = [(1,2), (2,2), (2,1), (2,0), (1,0), (0,0), (0,1), (0,2)]
    
    for r, c in positions:
        piece = generate_valid_piece(grid, r, c)
        grid[r][c] = piece
    
    return grid

def generate_valid_piece(grid, row, col):
    """Generate a piece that matches all adjacent pieces"""
    piece = [None, None, None, None]  # [T, R, B, L]
    constraints = []
    
    if row > 0 and grid[row-1][col]:  # Top neighbor
        piece[0] = opposite_side(grid[row-1][col][2])
    if col < 2 and grid[row][col+1]:  # Right neighbor
        piece[1] = opposite_side(grid[row][col+1][3])
    if row < 2 and grid[row+1][col]:  # Bottom neighbor
        piece[2] = opposite_side(grid[row+1][col][0])
    if col > 0 and grid[row][col-1]:  # Left neighbor
        piece[3] = opposite_side(grid[row][col-1][1])
    
    # Fill unconstrained sides with random colors
    colors = 'RrPpYyBbGg'
    for i in range(4):
        if piece[i] is None:
            piece[i] = random.choice(colors)
    
    return piece

def scramble_puzzle(grid):
    """Scramble by shuffling positions and random rotations"""
    flat = [piece for row in grid for piece in row]
    random.shuffle(flat)
    
    # Apply random rotations
    flat = [rotate_piece(piece.copy(), random.randint(0, 3)) for piece in flat]
    
    return [flat[i*3:(i+1)*3] for i in range(3)]

# Generate and output
solved = generate_puzzle()
print("Solved Puzzle:")
for row in solved:
    print(row)

scrambled = scramble_puzzle([row[:] for row in solved])
print("\nScrambled Puzzle:")
for row in scrambled:
    print(row)