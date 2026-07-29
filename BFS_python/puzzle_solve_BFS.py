import numpy as np
import sys
import os
import BFS_python.catPuzzleHandling as surgeon
import BFS_python.BFS_functions as BFS
# Since the function only returns one thing, we only need one variable here!
puzzleData, n, numPuzzles = surgeon.load_puzzles()
#initialize rng
rng = np.random.default_rng()

for i in range(numPuzzles):
    #load puzzle data for this loop
    initialBoard = puzzleData[i]
    #vectorize board
    vectored_board = surgeon.board_to_bits_vector(initialBoard)
    #Copies a board for elimination
    availablePieces = vectored_board.copy()
    #initiaze the solving board (2D) with zeroes
    solvingBoard = np.zeros((n, n), dtype=np.uint16)
    #Places first piece
    starter_idx = rng.integers(availablePieces.size)
    solvingBoard[0, 0] = availablePieces[starter_idx]
    #pops first piece from pool
    availablePieces = surgeon.swap_pop(availablePieces, starter_idx)
    #Starts BFS
    bfs_all_cases = []
    
    case = []
    
        for layer in range(2*n-2):
            #Transcribes matching sides from board
            matching_sides = BFS.transcribe_sides(solvingBoard, layer)
            #print([f"{value:08b}" for value in matching_sides])    just for seeing matching sides
            for corner in matching_sides:
                idx, piece = BFS.find_matching_piece(corner,availablePieces)
                if idx == -1:
                    #No match found for this corner, discard this case
                    break
                availablePieces = surgeon.swap_pop(availablePieces, idx)
                #Places piece on board
