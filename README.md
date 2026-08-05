How to search for "unicorn" (one solution) puzzles:
Run puzzle_gen_nxn_writeToFile_sterilize.py
  Enter puzzle size: size of puzzle you want (nxn)
  Number of puzzles: total number of puzzles in dataset
  (P.S. For 6x6 puzzles, it takes on average 20ms for a puzzle. (12600kf) 300000 took 10 hours for me, the time should scale lineraly)

You will obtain a dataset (for example scrambledPuzzles_6x6_100000.txt) in the same folder as the generator.

(IMPORTANT: Do not change the name of the dataset, the searcher depends on it)

Next, compile puzzle_solver_rotational_unique.cpp
In Visual studio Code, it will automatically run it.

How to run:
Plan A
1. In a terminal, go to the project folder and enter the file path of the compilled puzzle_solver_rotational_unique.exe
2. Press enter 
3. Enter the filepath of the dataset to be solved
4. Press enter

Plan B
1. In a terminal, go to the project folder and enter the file path of the compilled puzzle_solver_rotational_unique.exe
2. Press space
3. Enter the filepath of the dataset to be solved
   (optional)
5. Press space
6. Enter number of threads you want to use
7. Press Enter

The program will report every time it finishes a puzzle.
If it appears stuck, then your'e lucky: it's having a hard time finding solutions in this puzzle.

For 6x6, a puzzle could take hours. As long as the CPU is computing, it is not stuck.

When the program finds the unicorn, it will stop and report the stats in the terminal. Make sure to not power off or you will lose it forever.

Enjoy!
