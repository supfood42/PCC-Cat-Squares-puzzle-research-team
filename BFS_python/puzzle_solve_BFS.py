import numpy as np
import BFS_python.catPuzzleHandling as surgeon

# Since the function only returns one thing, we only need one variable here!
puzzleData, n, numPuzzles = surgeon.load_puzzles()
#initialize rng
rng = np.random.default_rng()

for i in range(numPuzzles):
    #load puzzle data for this loop
    initialBoard = puzzleData[i]
    #vectorize board
    vectored_board = surgeon.board_to_bits_vector(initialBoard)
    # Compute every piece's four rotations once, before the search starts.
    rotation_table = surgeon.build_rotation_table(vectored_board)
    # Store physical piece IDs so rotations still refer to the same piece.
    availablePieceIds = np.arange(vectored_board.size)
    #initiaze the solving board (2D) with zeroes
    solvingBoard = np.zeros((n, n), dtype=np.uint16)
    #Places first piece
    starter_idx = rng.integers(availablePieceIds.size)
    starter_id = availablePieceIds[starter_idx]
    solvingBoard[0, 0] = rotation_table[starter_id, 0]
    #pops first piece from pool
    availablePieceIds = surgeon.swap_pop(availablePieceIds, starter_idx)
    #Starts BFS
    bfs_all_cases = []
    
    case = []
    
    for layer in range(2*n-2):
        #Transcribes matching sides from board
        matching_sides = surgeon.transcribe_sides(solvingBoard, layer)
        #print([f"{value:08b}" for value in matching_sides])    just for seeing matching sides
        for corner in matching_sides:
            idx, piece = surgeon.find_matching_piece(
                corner,
                availablePieceIds,
                rotation_table,
            )
            if idx == -1:
                #No match found for this corner, discard this case
                break
            availablePieceIds = surgeon.swap_pop(availablePieceIds, idx)
            #Places piece on board
