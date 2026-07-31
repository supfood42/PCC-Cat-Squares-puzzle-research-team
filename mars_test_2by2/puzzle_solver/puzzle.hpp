// puzzle.hpp
// Ports of: code1_convert_pieces.py, puzzle_checks.py, piece_types.py,
// compatibility.py
#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "bits.hpp"

using Edges = std::array<int, 4>;   // top, right, bottom, left
using Corners = std::array<int, 4>; // top-left, top-right, bottom-right, bottom-left

// ============================================================
// CORNER ID CONVERSION  (code1_convert_pieces.py)
// ============================================================

inline const std::array<int, 8> VALUE_ORDER = {1, 2, 3, 4, -1, -2, -3, -4};

inline int valueIndex(int value) {
    for (int i = 0; i < 8; ++i)
        if (VALUE_ORDER[i] == value) return i;
    throw std::invalid_argument("Corner values must be one of {1,2,3,4,-1,-2,-3,-4}.");
}

inline int pairToCornerId(int first, int second) {
    return valueIndex(first) * 8 + valueIndex(second) + 1;
}

inline Corners pieceToCorners(const Edges &e) {
    int top = e[0], right = e[1], bottom = e[2], left = e[3];
    return {
        pairToCornerId(left, top),
        pairToCornerId(top, right),
        pairToCornerId(right, bottom),
        pairToCornerId(bottom, left),
    };
}

// ============================================================
// PARSING  (puzzle_checks.py / code1_convert_pieces.py)
// ============================================================

inline bool isAllowedValue(int v) {
    return v == 1 || v == 2 || v == 3 || v == 4 || v == -1 || v == -2 || v == -3 || v == -4;
}

// Parses "top right bottom left" lines, one piece per line, blank lines skipped.
inline std::vector<Edges> parsePieceText(const std::string &text) {
    std::vector<Edges> pieces;
    std::istringstream stream(text);
    std::string line;
    int lineNumber = 0;

    while (std::getline(stream, line)) {
        ++lineNumber;
        std::istringstream lineStream(line);
        std::vector<int> values;
        int v;
        std::string token;
        bool blank = true;
        std::istringstream tokenCheck(line);
        while (tokenCheck >> token) blank = false;
        if (blank) continue;

        std::istringstream parse(line);
        while (parse >> token) {
            try {
                size_t pos;
                v = std::stoi(token, &pos);
                if (pos != token.size()) throw std::invalid_argument("bad token");
            } catch (...) {
                throw std::invalid_argument(
                    "Line " + std::to_string(lineNumber) + " contains a non-integer value.");
            }
            values.push_back(v);
        }

        if (values.size() != 4) {
            throw std::invalid_argument(
                "Line " + std::to_string(lineNumber) + " must contain exactly four values.");
        }

        for (int val : values) {
            if (!isAllowedValue(val)) {
                throw std::invalid_argument(
                    "Line " + std::to_string(lineNumber) + " contains an invalid value: " +
                    std::to_string(val));
            }
        }

        pieces.push_back({values[0], values[1], values[2], values[3]});
    }

    return pieces;
}

// ============================================================
// GLOBAL CHECKS  (puzzle_checks.py)
// ============================================================

inline int determineBoardSize(int numberOfPieces) {
    int n = static_cast<int>(std::llround(std::sqrt(static_cast<double>(numberOfPieces))));
    // adjust for floating point edge cases
    while (n * n > numberOfPieces) --n;
    while ((n + 1) * (n + 1) <= numberOfPieces) ++n;
    if (n * n != numberOfPieces) {
        throw std::invalid_argument(
            std::to_string(numberOfPieces) + " pieces cannot form a square n x n puzzle.");
    }
    return n;
}

struct GlobalCheckResult {
    bool possible = false;
    std::string reason;
    int n = 0;
    std::array<int, 5> symbolCounts{}; // index 1..4 heads, use negative lookup separately
    std::map<int, int> countByValue;   // signed value -> count
    std::array<int, 5> discrepancy{};  // color 1..4
    int minimumBoundaryEdges = 0;
    int availableBoundaryEdges = 0;
};

inline GlobalCheckResult runGlobalChecks(const std::vector<Edges> &pieces) {
    GlobalCheckResult result;

    if (pieces.empty()) {
        result.possible = false;
        result.reason = "No pieces were entered.";
        return result;
    }

    int n;
    try {
        n = determineBoardSize(static_cast<int>(pieces.size()));
    } catch (const std::exception &e) {
        result.possible = false;
        result.reason = e.what();
        return result;
    }
    result.n = n;

    std::map<int, int> counts;
    for (const auto &piece : pieces)
        for (int e : piece) counts[e]++;
    result.countByValue = counts;

    for (int color = 1; color <= 4; ++color) {
        int heads = counts.count(color) ? counts[color] : 0;
        int bodies = counts.count(-color) ? counts[-color] : 0;
        result.discrepancy[color] = heads - bodies;
    }

    int requiredBoundary = 0;
    for (int color = 1; color <= 4; ++color) requiredBoundary += std::abs(result.discrepancy[color]);
    result.minimumBoundaryEdges = requiredBoundary;
    result.availableBoundaryEdges = 4 * n;

    if (requiredBoundary > result.availableBoundaryEdges) {
        result.possible = false;
        result.reason = "The head-body discrepancy requires at least " +
                         std::to_string(requiredBoundary) + " boundary edges, but an " +
                         std::to_string(n) + " x " + std::to_string(n) + " puzzle has only " +
                         std::to_string(result.availableBoundaryEdges) + ".";
        return result;
    }

    // Parity check
    int requiredMinimum = 0;
    for (int color = 1; color <= 4; ++color) {
        int heads = counts.count(color) ? counts[color] : 0;
        int bodies = counts.count(-color) ? counts[-color] : 0;
        int totalColorEdges = heads + bodies;
        int difference = std::abs(heads - bodies);
        int boundaryCount = difference;
        if (boundaryCount % 2 != totalColorEdges % 2) boundaryCount += 1;
        requiredMinimum += boundaryCount;
    }

    if (requiredMinimum > 4 * n) {
        result.possible = false;
        result.reason = "The color totals and boundary size have incompatible odd/even parity.";
        return result;
    }

    result.possible = true;
    result.reason = "The puzzle passed the preliminary global checks.";
    return result;
}

// ============================================================
// PIECE TYPES  (piece_types.py)
// ============================================================

inline Edges rotateClockwise(const Edges &e) {
    // Python: left, top, right, bottom
    return {e[3], e[0], e[1], e[2]};
}

inline std::array<Edges, 4> allRotations(const Edges &e) {
    std::array<Edges, 4> out;
    Edges cur = e;
    for (int i = 0; i < 4; ++i) {
        out[i] = cur;
        cur = rotateClockwise(cur);
    }
    return out;
}

inline Edges canonicalPiece(const Edges &e) {
    auto rots = allRotations(e);
    return *std::min_element(rots.begin(), rots.end());
}

inline std::vector<Edges> uniqueRotations(const Edges &e) {
    auto rots = allRotations(e);
    std::vector<Edges> out;
    for (auto &r : rots)
        if (std::find(out.begin(), out.end(), r) == out.end()) out.push_back(r);
    return out;
}

struct PieceType {
    int typeId;           // 1-based
    Edges canonicalEdges;
    int count;             // physical copies
    std::vector<int> sourcePieceNumbers;
    std::vector<Edges> rotations; // rotation_id == index
};

inline std::vector<PieceType> buildPieceTypes(const std::vector<Edges> &pieces) {
    std::map<Edges, std::vector<int>> grouped;
    for (size_t i = 0; i < pieces.size(); ++i) {
        Edges canon = canonicalPiece(pieces[i]);
        grouped[canon].push_back(static_cast<int>(i) + 1);
    }

    std::vector<PieceType> types;
    int typeId = 1;
    for (auto &[canon, sourceNumbers] : grouped) { // std::map iterates sorted, matching Python's sorted()
        PieceType pt;
        pt.typeId = typeId++;
        pt.canonicalEdges = canon;
        pt.count = static_cast<int>(sourceNumbers.size());
        pt.sourcePieceNumbers = sourceNumbers;
        pt.rotations = uniqueRotations(canon);
        types.push_back(std::move(pt));
    }
    return types;
}

// ============================================================
// CANDIDATES + COMPATIBILITY  (compatibility.py)
// ============================================================

struct Candidate {
    int typeId;
    int rotationId;
    Edges edges;
    Corners corners;
};

struct CompatibilityData {
    std::vector<Candidate> candidates; // flattened, index = candidate id
    std::vector<Bits> above, right, below, left; // per candidate: allowed neighbor set
    std::vector<Bits> typeMask; // index by typeId (1-based), bit set = candidate belongs to type
    std::vector<double> rarity; // per candidate
    int numCandidates = 0;
};

inline CompatibilityData prepareCompatibility(const std::vector<PieceType> &pieceTypes) {
    CompatibilityData data;

    for (const auto &pt : pieceTypes) {
        for (size_t r = 0; r < pt.rotations.size(); ++r) {
            Candidate c;
            c.typeId = pt.typeId;
            c.rotationId = static_cast<int>(r);
            c.edges = pt.rotations[r];
            c.corners = pieceToCorners(c.edges);
            data.candidates.push_back(c);
        }
    }

    int M = static_cast<int>(data.candidates.size());
    data.numCandidates = M;

    // Group candidate indices by each edge value on each side.
    std::map<int, std::vector<int>> byTop, byRight, byBottom, byLeft;
    for (int i = 0; i < M; ++i) {
        const auto &e = data.candidates[i].edges;
        byTop[e[0]].push_back(i);
        byRight[e[1]].push_back(i);
        byBottom[e[2]].push_back(i);
        byLeft[e[3]].push_back(i);
    }

    auto toBits = [&](const std::map<int, std::vector<int>> &groups, int key) -> Bits {
        Bits b(M);
        auto it = groups.find(key);
        if (it != groups.end())
            for (int idx : it->second) b.set(idx);
        return b;
    };

    data.above.resize(M);
    data.right.resize(M);
    data.below.resize(M);
    data.left.resize(M);
    data.rarity.resize(M);

    for (int i = 0; i < M; ++i) {
        const auto &e = data.candidates[i].edges;
        int top = e[0], right = e[1], bottom = e[2], left = e[3];

        // "above" = candidates that may sit above this one: their bottom == -top
        data.above[i] = toBits(byBottom, -top);
        // "right" = candidates that may sit to the right: their left == -right
        data.right[i] = toBits(byLeft, -right);
        // "below" = candidates that may sit below: their top == -bottom
        data.below[i] = toBits(byTop, -bottom);
        // "left" = candidates that may sit to the left: their right == -left
        data.left[i] = toBits(byRight, -left);

        int totalOptions = data.above[i].count() + data.right[i].count() +
                            data.below[i].count() + data.left[i].count();
        data.rarity[i] = 1.0 / std::max(totalOptions, 1);
    }

    int maxTypeId = 0;
    for (auto &pt : pieceTypes) maxTypeId = std::max(maxTypeId, pt.typeId);
    data.typeMask.assign(maxTypeId + 1, Bits(M));
    for (int i = 0; i < M; ++i) data.typeMask[data.candidates[i].typeId].set(i);

    return data;
}
