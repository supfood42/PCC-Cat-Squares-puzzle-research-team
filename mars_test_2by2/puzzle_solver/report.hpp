// report.hpp
#pragma once
#include <algorithm>
#include <fstream>
#include <string>
#include <vector>

#include "puzzle.hpp"
#include "solver.hpp"
#include "stats.hpp"

inline std::string pieceLabel(const Candidate &c) {
    return "T" + std::to_string(c.typeId) + "/R" + std::to_string(c.rotationId);
}

// Adds one solved board's evidence into the learning tables that
// actually affect search order (see stats.hpp for what is/isn't kept).
inline void recordSolutionStatistics(FrequencyStats &stats, const std::vector<int> &solution, int n,
                                      const CompatibilityData &compat) {
    auto inc = [](std::unordered_map<std::string, long long> &table, const std::string &key) {
        table[key] += 1;
    };

    for (int row = 0; row < n; ++row) {
        for (int col = 0; col < n; ++col) {
            int candIdx = solution[row * n + col];
            const Candidate &c = compat.candidates[candIdx];
            std::string category = boardPositionCategory(row, col, n);
            auto *table = category == "board_corner"   ? &stats.cornerBoardCorner
                          : category == "board_edge"    ? &stats.cornerBoardEdge
                                                         : &stats.cornerInterior;
            for (int cornerId : c.corners) inc(*table, std::to_string(cornerId));
        }
    }

    for (int row = 1; row < n; ++row) {
        for (int col = 1; col < n; ++col) {
            int a = solution[(row - 1) * n + (col - 1)];
            int b = solution[(row - 1) * n + col];
            int c = solution[row * n + (col - 1)];
            int d = solution[row * n + col];
            std::array<int, 4> junction = {
                compat.candidates[a].corners[2],
                compat.candidates[b].corners[3],
                compat.candidates[d].corners[0],
                compat.candidates[c].corners[1],
            };
            inc(stats.junctionFrequency, junctionKey(junction));
        }
    }

    for (int row = 0; row < n; ++row) {
        for (int col = 0; col < n; ++col) {
            int candIdx = solution[row * n + col];
            std::string candidateValue = edgesKey(compat.candidates[candIdx].edges);

            std::string topValue = "BOUNDARY";
            if (row > 0) topValue = edgesKey(compat.candidates[solution[(row - 1) * n + col]].edges);

            std::string leftValue = "BOUNDARY";
            if (col > 0) leftValue = edgesKey(compat.candidates[solution[row * n + col - 1]].edges);

            std::string key = "top=" + topValue + "|left=" + leftValue + "|candidate=" + candidateValue;
            inc(stats.neighborCandidateFrequency, key);
        }
    }

    stats.puzzlesRecorded += 1;
    stats.solutionsRecorded += 1;
}

inline void appendTopEntries(std::ofstream &out, const std::string &title,
                              const std::unordered_map<std::string, long long> &table, int limit) {
    out << title << "\n" << std::string(75, '-') << "\n";
    std::vector<std::pair<std::string, long long>> items(table.begin(), table.end());
    std::sort(items.begin(), items.end(),
              [](const auto &a, const auto &b) { return a.second > b.second; });
    if (items.empty()) {
        out << "(no data)\n";
    } else {
        int shown = 0;
        for (auto &[k, v] : items) {
            if (shown++ >= limit) break;
            out << k << ": " << v << "\n";
        }
    }
    out << "\n";
}

inline void writeFrequencyReport(const FrequencyStats &stats, const std::string &path) {
    std::ofstream out(path, std::ios::trunc);
    out << "FREQUENCY STATISTICS REPORT\n" << std::string(75, '=') << "\n\n";
    out << "Schema version: " << stats.schemaVersion << "\n";
    out << "Puzzles recorded: " << stats.puzzlesRecorded << "\n";
    out << "Solutions recorded: " << stats.solutionsRecorded << "\n\n";

    appendTopEntries(out, "CORNER IDS AT BOARD_CORNER", stats.cornerBoardCorner, 20);
    appendTopEntries(out, "CORNER IDS AT BOARD_EDGE", stats.cornerBoardEdge, 20);
    appendTopEntries(out, "CORNER IDS AT INTERIOR", stats.cornerInterior, 20);
    appendTopEntries(out, "MOST COMMON ORIENTED INTERNAL JUNCTIONS", stats.junctionFrequency, 50);
    appendTopEntries(out, "MOST COMMON TOP/LEFT NEIGHBOR CANDIDATES", stats.neighborCandidateFrequency, 50);

    out << std::string(75, '=') << "\nEND OF REPORT\n";
}

struct TimingInfo {
    double preprocessing = 0.0;
    double search = 0.0;
    double total = 0.0;
};

inline void writeSolverReport(const std::string &path, int n, int physicalPieces, int distinctTypes,
                               const CompatibilityData &compat, const GlobalCheckResult &check,
                               const std::array<int, 5> &discrepancy, long long solutionCount,
                               const SolveStatistics &stats,
                               const std::vector<std::vector<int>> &solutions,
                               const TimingInfo &timing) {
    std::ofstream out(path, std::ios::trunc);
    out << "N x N PUZZLE SOLVER REPORT (C++)\n" << std::string(80, '=') << "\n\n";
    out << "Board size: " << n << " x " << n << "\n";
    out << "Physical pieces: " << physicalPieces << "\n";
    out << "Distinct piece types: " << distinctTypes << "\n";
    out << "Distinct type-and-rotation candidates: " << compat.numCandidates << "\n";
    out << "Solutions found: " << solutionCount << "\n";
    out << "Complete boards stored: " << solutions.size() << "\n\n";

    out << "GLOBAL CHECKS\n" << std::string(80, '-') << "\n";
    out << check.reason << "\n";
    out << "Minimum required boundary edges: " << check.minimumBoundaryEdges << "\n";
    out << "Available boundary edges: " << check.availableBoundaryEdges << "\n\n";

    out << "SEARCH STATISTICS\n" << std::string(80, '-') << "\n";
    out << "Recursive calls: " << stats.recursiveCalls << "\n";
    out << "Candidate attempts: " << stats.candidateAttempts << "\n";
    out << "Accepted partial placements: " << stats.placementsAccepted << "\n";
    out << "Backtracks: " << stats.backtracks << "\n";
    out << "Dead ends: " << stats.deadEnds << "\n\n";

    out << "TIMING\n" << std::string(80, '-') << "\n";
    out << "Preprocessing time: " << timing.preprocessing << " seconds\n";
    out << "Search time: " << timing.search << " seconds\n";
    out << "Total computation time: " << timing.total << " seconds\n\n";

    static const char *colorNames[5] = {"", "yellow", "pink", "purple", "green"};
    out << "BOUNDARY PRIORITY DATA\n" << std::string(80, '-') << "\n";
    for (int color = 1; color <= 4; ++color) {
        int d = discrepancy[color];
        out << colorNames[color] << ": ";
        if (d > 0) out << d << " excess head(s)\n";
        else if (d < 0) out << -d << " excess body/bodies\n";
        else out << "balanced\n";
    }
    out << "\n";

    if (!solutions.empty()) {
        out << std::string(80, '=') << "\nSOLUTION 1\n" << std::string(80, '=') << "\n\n";
        const auto &solution = solutions[0];

        out << "TYPE / ROTATION GRID\n" << std::string(80, '-') << "\n";
        for (int row = 0; row < n; ++row) {
            std::vector<std::string> labels;
            for (int col = 0; col < n; ++col)
                labels.push_back(pieceLabel(compat.candidates[solution[row * n + col]]));
            for (size_t i = 0; i < labels.size(); ++i) {
                out << labels[i];
                if (i + 1 < labels.size()) out << " | ";
            }
            out << "\n";
        }

        out << "\nDETAILED PLACEMENTS\n" << std::string(80, '-') << "\n";
        for (int row = 0; row < n; ++row) {
            for (int col = 0; col < n; ++col) {
                const Candidate &c = compat.candidates[solution[row * n + col]];
                out << "Position (" << row + 1 << ", " << col + 1 << ")\n";
                out << "  Piece type: " << c.typeId << "\n";
                out << "  Rotation: " << c.rotationId << "\n";
                out << "  Edges [top, right, bottom, left]: [" << c.edges[0] << ", " << c.edges[1]
                    << ", " << c.edges[2] << ", " << c.edges[3] << "]\n";
                out << "  Corners [top-left, top-right, bottom-right, bottom-left]: [" << c.corners[0]
                    << ", " << c.corners[1] << ", " << c.corners[2] << ", " << c.corners[3] << "]\n\n";
            }
        }

        out << "COMPLETED INTERNAL JUNCTIONS\n" << std::string(80, '-') << "\n";
        for (int row = 1; row < n; ++row) {
            for (int col = 1; col < n; ++col) {
                int a = solution[(row - 1) * n + (col - 1)];
                int b = solution[(row - 1) * n + col];
                int c = solution[row * n + (col - 1)];
                int d = solution[row * n + col];
                std::array<int, 4> junction = {
                    compat.candidates[a].corners[2],
                    compat.candidates[b].corners[3],
                    compat.candidates[d].corners[0],
                    compat.candidates[c].corners[1],
                };
                out << "Junction at grid crossing (" << row << ", " << col << "): ["
                    << junction[0] << ", " << junction[1] << ", " << junction[2] << ", "
                    << junction[3] << "]\n";
            }
        }
    }

    out << "\n" << std::string(80, '=') << "\nEND OF REPORT\n";
}
