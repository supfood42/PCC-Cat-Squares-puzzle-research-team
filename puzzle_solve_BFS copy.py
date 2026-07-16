import math
import sys
import time

def get_rotations(piece):
    """
    Returns all 4 valid 90-degree rotations of a piece.
    Assuming the format is [Top, Right, Bottom, Left].
    """
    return [
        piece,
        [piece[3], piece[0], piece[1], piece[2]], # Rotated 90 deg clockwise
        [piece[2], piece[3], piece[0], piece[1]], # Rotated 180 deg
        [piece[1], piece[2], piece[3], piece[0]]  # Rotated 270 deg
    ]

def solve_layer_by_layer(pieces):
    n = int(math.sqrt(len(pieces)))
    
    # Define Layer Traversal Order
    cells_by_layer = []
    for d in range(2 * n - 1):
        for i in range(n):
            j = d - i
            if 0 <= j < n:
                cells_by_layer.append((i, j))
                
    grid = [[None for _ in range(n)] for _ in range(n)]
    used = [False] * len(pieces)
    
    # Simple counter to show progress/activity during search
    states_explored = 0
    
    def backtrack(cell_idx):
        nonlocal states_explored
        states_explored += 1
        
        # Base Case: All layers successfully filled
        if cell_idx == len(cells_by_layer):
            return True
            
        r, c = cells_by_layer[cell_idx]
        
        # Try placing every unused piece in all possible rotations
        for i in range(len(pieces)):
            if not used[i]:
                for rot in get_rotations(pieces[i]):
                    
                    # Check Top neighbor
                    if r > 0 and grid[r-1][c] is not None:
                        if grid[r-1][c][2] + rot[0] != 0:
                            continue
                            
                    # Check Left neighbor
                    if c > 0 and grid[r][c-1] is not None:
                        if grid[r][c-1][1] + rot[3] != 0:
                            continue
                            
                    # Place the piece
                    grid[r][c] = rot
                    used[i] = True
                    
                    # Move to the next cell in the layer
                    if backtrack(cell_idx + 1):
                        return True
                        
                    # Revert if conflict occurs
                    used[i] = False
                    grid[r][c] = None
                    
        return False

    print("\n[Running] Initiating solver and mapping layers...")
    
    # Start timer
    start_time = time.perf_counter()
    success = backtrack(0)
    end_time = time.perf_counter()
    
    # Calculate duration
    elapsed_time = end_time - start_time
    
    # Clear the inline progress counter line
    print("\r" + " " * 50 + "\r", end="") 
    print(f"[Done] Search finished.")
    print(f"Total states explored: {states_explored:,}")
    print(f"Time elapsed: {elapsed_time:.4f} seconds")
    
    return grid if success else None

def print_solution(grid):
    print("\n--- Solution ---")
    # Prints left-to-right, top-to-bottom, one piece per line
    for row in grid:
        for piece in row:
            print(" ".join(map(str, piece)))

if __name__ == "__main__":
    print("=== Edge Matching Puzzle Solver ===")
    print("Enter puzzle below (paste your list of pieces, then press ENTER on a blank line to solve):")
    print("-" * 50)
    
    # Read line-by-line until a blank line is entered
    lines = []
    while True:
        line = input()
        if not line.strip(): # Stop if the user presses Enter on an empty line
            break
        lines.append(line)
    
    # Parse the input pieces
    pieces = []
    for line in lines:
        try:
            pieces.append(list(map(int, line.strip().split())))
    #------Redundancies------------------------------------------------------------------------
        except ValueError:
            print(f"Error parsing line: '{line}'. Please ensure it only contains numbers.")
            sys.exit(1)
                
    if not pieces:
        print("No pieces entered. Exiting.")
        sys.exit(1)
        
    # Check if the number of pieces forms a perfect square grid
    n = math.sqrt(len(pieces))
    if n % 1 != 0:
        print(f"Error: The number of pieces ({len(pieces)}) must be a perfect square (e.g., 9, 16, 25).")
        sys.exit(1)
    #-------------------------------------------------   
    # Solve
    solution = solve_layer_by_layer(pieces)
    #---------------------------------------------------
    if solution:
        print_solution(solution)
    else:
        print("\nNo solution exists for this configuration.")