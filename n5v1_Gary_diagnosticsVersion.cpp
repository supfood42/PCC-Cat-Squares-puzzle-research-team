#include <iostream>
#include <fstream>
#include <chrono>
#include <cmath>
#include <string>
#include <thread>
#include <atomic>
#include <iomanip>

using namespace std;

const int MAX_N = 20;
const int MAX_PIECES = MAX_N * MAX_N;

struct Edge
{
    int value;
};

struct Piece
{
    Edge e[4];
};

struct Cell
{
    int id;
    int rot;
    Piece p;
};

Piece pieces[MAX_PIECES];
Piece rot[MAX_PIECES][4];

Cell board[MAX_N][MAX_N];

bool used[MAX_PIECES];

long long nodes = 0;

// True when the current DFS has found a solution.
bool foundSolution = false;

// ============================================================
// Statistics
// ============================================================

atomic<unsigned long long> puzzlesProcessed{0};
atomic<unsigned long long> puzzlesSolved{0};
atomic<unsigned long long> puzzlesNoSolution{0};

atomic<bool> programFinished{false};

chrono::steady_clock::time_point globalStart;


// ============================================================
// Match two edges
// ============================================================

bool match(Edge a, Edge b)
{
    return abs(a.value) == abs(b.value) &&
           a.value + b.value == 0;
}


// ============================================================
// Rotate piece 90 degrees clockwise
// ============================================================

Piece rotate90(Piece p)
{
    Piece q;

    q.e[0] = p.e[3];
    q.e[1] = p.e[0];
    q.e[2] = p.e[1];
    q.e[3] = p.e[2];

    return q;
}


// ============================================================
// Build all rotations
// ============================================================

void build_rotations(int pieceCount)
{
    for (int i = 0; i < pieceCount; i++)
    {
        rot[i][0] = pieces[i];

        for (int r = 1; r < 4; r++)
            rot[i][r] = rotate90(rot[i][r - 1]);
    }
}


// ============================================================
// Check whether current piece fits
// ============================================================

bool valid(int r, int c)
{
    Piece& cur = board[r][c].p;

    // Top
    if (r > 0)
    {
        if (!match(
                cur.e[0],
                board[r - 1][c].p.e[2]))
        {
            return false;
        }
    }

    // Left
    if (c > 0)
    {
        if (!match(
                cur.e[3],
                board[r][c - 1].p.e[1]))
        {
            return false;
        }
    }

    return true;
}


// ============================================================
// DFS
//
// IMPORTANT:
// This version stops immediately after finding ONE solution.
// ============================================================

bool dfs(int pos, int n)
{
    nodes++;

    if (pos == n * n)
    {
        foundSolution = true;
        return true;
    }

    int r = pos / n;
    int c = pos % n;

    for (int i = 0; i < n * n; i++)
    {
        if (used[i])
            continue;

        for (int k = 0; k < 4; k++)
        {
            board[r][c].id = i;
            board[r][c].rot = k;
            board[r][c].p = rot[i][k];

            if (valid(r, c))
            {
                used[i] = true;

                if (dfs(pos + 1, n))
                {
                    return true;
                }

                used[i] = false;
            }
        }
    }

    return false;
}


// ============================================================
// Reset solver state for a new puzzle
// ============================================================

void reset_solver(int pieceCount)
{
    foundSolution = false;
    nodes = 0;

    for (int i = 0; i < pieceCount; i++)
        used[i] = false;
}


// ============================================================
// Solve one puzzle
// ============================================================

bool solve_puzzle(int n)
{
    const int pieceCount = n * n;

    reset_solver(pieceCount);

    build_rotations(pieceCount);

    return dfs(0, n);
}


// ============================================================
// Reporter thread
//
// Prints every INTERVAL_SECONDS seconds:
//
// Time elapsed
// Total puzzles solved
// Puzzles solved within interval
// Average time / puzzle
// Puzzles processed
// No-solution puzzles
// ============================================================

void statistics_reporter(
    double intervalSeconds)
{
    unsigned long long previousSolved = 0;

    while (!programFinished.load())
    {
        this_thread::sleep_for(
            chrono::duration<double>(
                intervalSeconds
            )
        );

        if (programFinished.load())
            break;

        auto now =
            chrono::steady_clock::now();

        double elapsed =
            chrono::duration<double>(
                now - globalStart
            ).count();

        unsigned long long totalSolved =
            puzzlesSolved.load();

        unsigned long long totalProcessed =
            puzzlesProcessed.load();

        unsigned long long noSolution =
            puzzlesNoSolution.load();

        unsigned long long intervalSolved =
            totalSolved - previousSolved;

        previousSolved = totalSolved;

        double averageTime =
            totalSolved > 0
                ? elapsed /
                  static_cast<double>(totalSolved)
                : 0.0;

        cout
            << "\n========================================\n"
            << "Time elapsed:          "
            << fixed << setprecision(2)
            << elapsed
            << " s\n"

            << "Puzzles processed:     "
            << totalProcessed
            << '\n'

            << "Puzzles solved:        "
            << totalSolved
            << '\n'

            << "Solved this interval:  "
            << intervalSolved
            << '\n'

            << "No solution:           "
            << noSolution
            << '\n'

            << "Average time / puzzle: "
            << fixed << setprecision(6)
            << averageTime
            << " s\n"

            << "========================================\n"
            << flush;
    }
}


// ============================================================
// Print final statistics
// ============================================================

void print_final_statistics()
{
    auto end =
        chrono::steady_clock::now();

    double elapsed =
        chrono::duration<double>(
            end - globalStart
        ).count();

    unsigned long long processed =
        puzzlesProcessed.load();

    unsigned long long solved =
        puzzlesSolved.load();

    unsigned long long noSolution =
        puzzlesNoSolution.load();

    double averageTime =
        solved > 0
            ? elapsed /
              static_cast<double>(solved)
            : 0.0;

    cout
        << "\n\n"
        << "========================================\n"
        << "FINAL RESULTS\n"
        << "========================================\n"

        << "Total elapsed time:    "
        << fixed << setprecision(3)
        << elapsed
        << " s\n"

        << "Puzzles processed:     "
        << processed
        << '\n'

        << "Puzzles solved:        "
        << solved
        << '\n'

        << "No solution:           "
        << noSolution
        << '\n'

        << "Average time / puzzle: "
        << fixed << setprecision(6)
        << averageTime
        << " s\n";

    if (elapsed > 0.0)
    {
        double puzzlesPerSecond =
            solved / elapsed;

        cout
            << "Puzzles / second:      "
            << fixed << setprecision(3)
            << puzzlesPerSecond
            << '\n';
    }

    cout
        << "========================================\n";
}


// ============================================================
// Main
//
// Usage:
//
// automaticUnicornHunter.exe
//     scrambledPuzzles_6x6_100000.txt
//     6
//
// Optional third argument:
//
// automaticUnicornHunter.exe
//     scrambledPuzzles_6x6_100000.txt
//     6
//     10
//
// where 10 = statistics interval in seconds.
// ============================================================

int main(int argc, char* argv[])
{
    if (argc < 3)
    {
        cout
            << "Usage:\n"
            << "  " << argv[0]
            << " <dataset.txt> <N> [interval_seconds]\n\n"

            << "Example:\n"
            << "  " << argv[0]
            << " scrambledPuzzles_6x6_100000.txt 6 10\n";

        return 1;
    }

    string filename = argv[1];

    int n = 0;

    try
    {
        n = stoi(argv[2]);
    }
    catch (...)
    {
        cerr << "Invalid puzzle size.\n";
        return 1;
    }

    if (n < 2 || n > MAX_N)
    {
        cerr
            << "Puzzle size must be between 2 and "
            << MAX_N << ".\n";

        return 1;
    }

    double intervalSeconds = 10.0;

    if (argc >= 4)
    {
        try
        {
            intervalSeconds =
                stod(argv[3]);
        }
        catch (...)
        {
            cerr
                << "Invalid interval.\n";

            return 1;
        }

        if (intervalSeconds <= 0)
        {
            cerr
                << "Interval must be greater than 0.\n";

            return 1;
        }
    }


    // ========================================================
    // Open dataset
    // ========================================================

    ifstream input(filename);

    if (!input)
    {
        cerr
            << "Could not open dataset:\n"
            << filename
            << '\n';

        return 1;
    }


    const int pieceCount = n * n;


    cout
        << "Dataset: "
        << filename
        << '\n'

        << "Puzzle size: "
        << n << "x" << n
        << '\n'

        << "Pieces per puzzle: "
        << pieceCount
        << '\n'

        << "Statistics interval: "
        << intervalSeconds
        << " seconds\n\n";


    // ========================================================
    // Start global timer
    // ========================================================

    globalStart =
        chrono::steady_clock::now();


    // ========================================================
    // Start statistics thread
    // ========================================================

    thread reporter(
        statistics_reporter,
        intervalSeconds
    );


    // ========================================================
    // Read and solve every puzzle
    // ========================================================

    while (true)
    {
        bool gotPuzzle = true;

        // Read exactly N*N pieces.
        for (int i = 0;
             i < pieceCount;
             i++)
        {
            for (int j = 0;
                 j < 4;
                 j++)
            {
                if (!(input >>
                      pieces[i].e[j].value))
                {
                    gotPuzzle = false;
                    break;
                }
            }

            if (!gotPuzzle)
                break;
        }

        // EOF reached before another complete puzzle.
        if (!gotPuzzle)
            break;


        // ----------------------------------------------------
        // Solve this puzzle
        // ----------------------------------------------------

        bool solved =
            solve_puzzle(n);


        // ----------------------------------------------------
        // Update statistics
        // ----------------------------------------------------

        puzzlesProcessed.fetch_add(
            1,
            memory_order_relaxed
        );

        if (solved)
        {
            puzzlesSolved.fetch_add(
                1,
                memory_order_relaxed
            );
        }
        else
        {
            puzzlesNoSolution.fetch_add(
                1,
                memory_order_relaxed
            );
        }
    }


    // ========================================================
    // Stop reporter
    // ========================================================

    programFinished.store(
        true
    );

    reporter.join();


    // ========================================================
    // Final statistics
    // ========================================================

    print_final_statistics();

    return 0;
}