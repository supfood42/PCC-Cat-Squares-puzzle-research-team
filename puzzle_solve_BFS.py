import numpy
import sys
import os
from catPuzzleHandling import load_puzzles

# Since the function only returns one thing, we only need one variable here!
puzzleData, n, numPuzzles = load_puzzles()

for i in range(numPuzzles):
    initialBoard = puzzleData[i]
    