import numpy as np
import sys
import os
import catPuzzleHandling as surgeon
# Since the function only returns one thing, we only need one variable here!
puzzleData, n, numPuzzles = surgeon.load_puzzles()
#initialize rng
rng = np.random.default_rng()

for i in range(numPuzzles):
    #load puzzle data for this loop
    initialBoard = puzzleData[i]
    #vectorize board
    vectored_board = surgeon.board_to_bits_vector(initialBoard)
    #initiaze the solving board (2D) with zeroes
    solvingBoard = np.zeros((n, n), dtype=np.uint16)
    #Places first piece
    solvingBoard[0][0] = rng.choice(vectored_board)
    
    for layer in range(2*n-2):
        #Transcribes matching sides from board
        matching_sides = surgeon.transcribe_sides(solvingBoard, layer)
        print([f"{value:08b}" for value in matching_sides])