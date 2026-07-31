// stats.hpp
// Ports the parts of frequency_stats.py and scoring.py that actually
// influence search order (corner-position, junction, and top/left
// neighbor frequency tables). Tables that are recorded by the Python
// version purely for human-readable reporting and are never read back
// during solving (piece_position_frequency, horizontal/vertical pair
// frequency, block_frequency) are intentionally omitted here -- see
// the accompanying notes.
//
// This uses a small self-contained text format instead of JSON, so the
// C++ build has no external dependencies. It is NOT interchangeable
// with the Python project's frequency_stats.json.
#pragma once
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>

#include "puzzle.hpp"

struct FrequencyStats {
    long long schemaVersion = 2;
    long long puzzlesRecorded = 0;
    long long solutionsRecorded = 0;

    std::unordered_map<std::string, long long> cornerBoardCorner;
    std::unordered_map<std::string, long long> cornerBoardEdge;
    std::unordered_map<std::string, long long> cornerInterior;
    std::unordered_map<std::string, long long> junctionFrequency;
    std::unordered_map<std::string, long long> neighborCandidateFrequency;
};

inline std::string boardPositionCategory(int row, int column, int n) {
    bool onTopOrBottom = (row == 0 || row == n - 1);
    bool onLeftOrRight = (column == 0 || column == n - 1);
    if (onTopOrBottom && onLeftOrRight) return "board_corner";
    if (onTopOrBottom || onLeftOrRight) return "board_edge";
    return "interior";
}

inline void writeTable(std::ofstream &out, const std::string &header,
                        const std::unordered_map<std::string, long long> &table) {
    out << "[" << header << "]\n";
    for (const auto &[k, v] : table) out << k << "\t" << v << "\n";
}

inline void saveFrequencyStats(const FrequencyStats &stats, const std::string &path) {
    std::ofstream out(path, std::ios::trunc);
    out << "FREQSTATS v2\n";
    out << "schema_version\t" << stats.schemaVersion << "\n";
    out << "puzzles_recorded\t" << stats.puzzlesRecorded << "\n";
    out << "solutions_recorded\t" << stats.solutionsRecorded << "\n";
    writeTable(out, "corner_positions.board_corner", stats.cornerBoardCorner);
    writeTable(out, "corner_positions.board_edge", stats.cornerBoardEdge);
    writeTable(out, "corner_positions.interior", stats.cornerInterior);
    writeTable(out, "junction_frequency", stats.junctionFrequency);
    writeTable(out, "neighbor_candidate_frequency", stats.neighborCandidateFrequency);
}

inline FrequencyStats loadFrequencyStats(const std::string &path) {
    FrequencyStats stats;
    std::ifstream in(path);
    if (!in.good()) return stats; // no file yet -> blank statistics

    std::string line;
    std::unordered_map<std::string, long long> *currentTable = nullptr;
    std::getline(in, line); // header line "FREQSTATS v2"

    while (std::getline(in, line)) {
        if (line.empty()) continue;
        if (line.front() == '[') {
            std::string name = line.substr(1, line.size() - 2);
            if (name == "corner_positions.board_corner") currentTable = &stats.cornerBoardCorner;
            else if (name == "corner_positions.board_edge") currentTable = &stats.cornerBoardEdge;
            else if (name == "corner_positions.interior") currentTable = &stats.cornerInterior;
            else if (name == "junction_frequency") currentTable = &stats.junctionFrequency;
            else if (name == "neighbor_candidate_frequency") currentTable = &stats.neighborCandidateFrequency;
            else currentTable = nullptr;
            continue;
        }
        size_t tab = line.find('\t');
        if (tab == std::string::npos) continue;
        std::string key = line.substr(0, tab);
        long long value = std::stoll(line.substr(tab + 1));
        if (currentTable) {
            (*currentTable)[key] = value;
        } else {
            if (key == "schema_version") stats.schemaVersion = value;
            else if (key == "puzzles_recorded") stats.puzzlesRecorded = value;
            else if (key == "solutions_recorded") stats.solutionsRecorded = value;
        }
    }
    return stats;
}

inline std::string edgesKey(const Edges &e) {
    return std::to_string(e[0]) + "," + std::to_string(e[1]) + "," +
           std::to_string(e[2]) + "," + std::to_string(e[3]);
}

inline std::string junctionKey(const std::array<int, 4> &j) {
    return std::to_string(j[0]) + "," + std::to_string(j[1]) + "," +
           std::to_string(j[2]) + "," + std::to_string(j[3]);
}

// ============================================================
// SCORING HELPERS  (scoring.py)
// ============================================================

inline bool isBoundaryPosition(int row, int column, int n) {
    return row == 0 || row == n - 1 || column == 0 || column == n - 1;
}

inline std::array<int, 4> outwardEdgeIndexes(int row, int column, int n) {
    std::array<int, 4> idx{-1, -1, -1, -1};
    int c = 0;
    if (row == 0) idx[c++] = 0;
    if (column == n - 1) idx[c++] = 1;
    if (row == n - 1) idx[c++] = 2;
    if (column == 0) idx[c++] = 3;
    for (; c < 4; ++c) idx[c] = -1;
    return idx;
}

inline double edgeImbalanceScore(int edge, const std::array<int, 5> &discrepancy) {
    int color = std::abs(edge);
    double imbalance = discrepancy[color];
    return edge > 0 ? imbalance : -imbalance;
}

inline double boundaryRotationScore(const Edges &edges, int row, int column, int n,
                                     const std::array<int, 5> &discrepancy) {
    bool outward[4] = {row == 0, column == n - 1, row == n - 1, column == 0};
    double score = 0.0;
    for (int i = 0; i < 4; ++i) {
        if (outward[i]) {
            score += 2.0 * edgeImbalanceScore(edges[i], discrepancy);
        } else {
            double es = edgeImbalanceScore(edges[i], discrepancy);
            if (es > 0) score -= 0.5 * es;
        }
    }
    return score;
}

inline double positionTypeScore(const Edges &edges, int row, int column, int n,
                                 const std::array<int, 5> &discrepancy) {
    double totalExcess = 0.0;
    for (int e : edges) {
        double s = edgeImbalanceScore(e, discrepancy);
        if (s > 0) totalExcess += s;
    }
    return isBoundaryPosition(row, column, n) ? 0.25 * totalExcess : -0.25 * totalExcess;
}

inline double cornerFrequencyScore(const Corners &corners, int row, int column, int n,
                                    const FrequencyStats &stats) {
    if (stats.solutionsRecorded == 0) return 0.0;

    const std::unordered_map<std::string, long long> *table = nullptr;
    std::string category = boardPositionCategory(row, column, n);
    if (category == "board_corner") table = &stats.cornerBoardCorner;
    else if (category == "board_edge") table = &stats.cornerBoardEdge;
    else table = &stats.cornerInterior;

    long long total = 0;
    for (auto &[k, v] : *table) total += v;
    if (total == 0) return 0.0;

    double score = 0.0;
    for (int cornerId : corners) {
        auto it = table->find(std::to_string(cornerId));
        long long cornerCount = (it != table->end()) ? it->second : 0;
        score += static_cast<double>(cornerCount + 1) / static_cast<double>(total + 64);
    }
    return score;
}
