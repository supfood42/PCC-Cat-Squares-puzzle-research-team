// main.cpp
// C++ port of the edge-matching puzzle solver (puzzle_checks.py +
// piece_types.py + compatibility.py + scoring.py + solver.py +
// the scoring-relevant parts of frequency_stats.py).
//
// Usage:
//   ./puzzle_solver < pieces.txt
//   ./puzzle_solver pieces.txt
//
// Input format (same as the Python version): one piece per line,
// "top right bottom left", values from {1,2,3,4,-1,-2,-3,-4}, blank
// line or EOF ends input.
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

#include "puzzle.hpp"
#include "report.hpp"
#include "solver.hpp"
#include "stats.hpp"

// Tunable to match solver.py's settings.
static const long long MAX_SOLUTIONS = 1;
static const int MAX_STORED_SOLUTIONS = 1;
static const bool USE_CANDIDATE_SCORING = true;
static const char *FREQUENCY_STATS_FILE = "frequency_stats.dat";
static const char *SOLVER_REPORT_FILE = "solver_report_cpp.txt";
static const char *FREQUENCY_REPORT_FILE = "frequency_stats_report_cpp.txt";

static std::string readAllInput(std::istream &in) {
    std::ostringstream ss;
    std::string line;
    while (std::getline(in, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) break; // blank line ends input
        ss << line << "\n";
    }
    return ss.str();
}

int main(int argc, char **argv) {
    auto programStart = std::chrono::steady_clock::now();

    std::string text;
    if (argc > 1) {
        std::ifstream file(argv[1]);
        if (!file.good()) {
            std::cerr << "Could not open file: " << argv[1] << "\n";
            return 1;
        }
        std::ostringstream ss;
        ss << file.rdbuf();
        text = ss.str();
    } else {
        std::cout << "Paste all puzzle pieces.\n";
        std::cout << "Use one piece per line: top right bottom left\n";
        std::cout << "Press Enter on a blank line (or EOF) when finished.\n\n";
        text = readAllInput(std::cin);
    }

    std::vector<Edges> pieces;
    try {
        pieces = parsePieceText(text);
    } catch (const std::exception &e) {
        std::cerr << "\nInput error: " << e.what() << "\n";
        return 1;
    }

    auto preprocessingStart = std::chrono::steady_clock::now();

    GlobalCheckResult check = runGlobalChecks(pieces);
    if (!check.possible) {
        std::cout << "\nNO SOLUTION\n" << check.reason << "\n";
        return 0;
    }

    int n = check.n;
    auto pieceTypes = buildPieceTypes(pieces);
    std::vector<int> initialInventory(pieceTypes.size() + 1, 0);
    for (auto &pt : pieceTypes) initialInventory[pt.typeId] = pt.count;

    CompatibilityData compat = prepareCompatibility(pieceTypes);
    FrequencyStats stats = loadFrequencyStats(FREQUENCY_STATS_FILE);

    auto preprocessingEnd = std::chrono::steady_clock::now();

    Solver solver(n, compat, initialInventory, check.discrepancy, &stats, MAX_SOLUTIONS,
                  MAX_STORED_SOLUTIONS, USE_CANDIDATE_SCORING);
    solver.heartbeatInterval = 1000000;

    auto searchStart = std::chrono::steady_clock::now();
    solver.solve();
    auto searchEnd = std::chrono::steady_clock::now();

    TimingInfo timing;
    timing.preprocessing = std::chrono::duration<double>(preprocessingEnd - preprocessingStart).count();
    timing.search = std::chrono::duration<double>(searchEnd - searchStart).count();
    timing.total = std::chrono::duration<double>(searchEnd - preprocessingStart).count();

    if (!solver.solutions().empty()) {
        recordSolutionStatistics(stats, solver.solutions()[0], n, compat);
        saveFrequencyStats(stats, FREQUENCY_STATS_FILE);
        writeFrequencyReport(stats, FREQUENCY_REPORT_FILE);
    }

    writeSolverReport(SOLVER_REPORT_FILE, n, static_cast<int>(pieces.size()),
                       static_cast<int>(pieceTypes.size()), compat, check, check.discrepancy,
                       solver.solutionCount(), solver.statistics(), solver.solutions(), timing);

    auto programEnd = std::chrono::steady_clock::now();

    std::cout << "\nSolver finished.\n";
    std::cout << "Board size: " << n << " x " << n << "\n";
    std::cout << "Solutions found: " << solver.solutionCount() << "\n";
    if (solver.statistics().stoppedAtSolutionLimit) {
        std::cout << "Search stopped after reaching the " << MAX_SOLUTIONS << "-solution limit.\n";
    } else {
        std::cout << "The complete search space was exhausted.\n";
    }
    std::cout << "Search time: " << timing.search << " seconds\n";
    std::cout << "Total computation time: " << timing.total << " seconds\n";
    std::cout << "Candidate attempts: " << solver.statistics().candidateAttempts << "\n";
    std::cout << "Backtracks: " << solver.statistics().backtracks << "\n";
    std::cout << "Dead ends: " << solver.statistics().deadEnds << "\n";
    std::cout << "\nDetailed report written to: " << SOLVER_REPORT_FILE << "\n";
    std::cout << "Program total time: "
              << std::chrono::duration<double>(programEnd - programStart).count() << " seconds\n";

    return 0;
}
