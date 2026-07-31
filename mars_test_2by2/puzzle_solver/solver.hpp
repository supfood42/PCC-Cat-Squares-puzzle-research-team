// solver.hpp
// Port of the recursive most-constrained-position backtracking search
// in solver.py. The algorithm (MRV position choice, duplicate-piece
// inventory, scored candidate ordering) is unchanged; the difference
// is representation: candidate domains are intersected as fixed-size
// bitsets (a handful of 64-bit words) instead of Python sets of
// (type_id, rotation_id) tuples, and everything runs compiled instead
// of interpreted.
#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <iostream>
#include <optional>
#include <vector>


#include "bits.hpp"
#include "puzzle.hpp"
#include "stats.hpp"

struct SolveStatistics {
    long long recursiveCalls = 0;
    long long candidateAttempts = 0;
    long long placementsAccepted = 0;
    long long backtracks = 0;
    long long deadEnds = 0;
    bool stoppedAtSolutionLimit = false;
};

class Solver {
public:
    Solver(int n, const CompatibilityData &compat, const std::vector<int> &initialInventory,
           const std::array<int, 5> &discrepancy, const FrequencyStats *stats,
           long long maxSolutions, int maxStoredSolutions, bool useCandidateScoring)
        : n_(n), compat_(compat), discrepancy_(discrepancy), stats_(stats),
          maxSolutions_(maxSolutions), maxStoredSolutions_(maxStoredSolutions),
          useCandidateScoring_(useCandidateScoring) {
        int M = compat_.numCandidates;
        grid_.assign(n_ * n_, -1);
        remainingInventory_ = initialInventory;

        fullMask_ = Bits(M);
        fullMask_.setAll();

        availableMask_ = Bits(M);
        for (size_t t = 1; t < compat_.typeMask.size(); ++t) {
            if (t < remainingInventory_.size() && remainingInventory_[t] > 0)
                availableMask_ |= compat_.typeMask[t];
        }

        useFrequencyScoring_ = (stats_ != nullptr && stats_->solutionsRecorded > 0);
    }

    void solve() {
        searchStart_ = std::chrono::steady_clock::now();
        search();
    }

    const std::vector<std::vector<int>> &solutions() const { return storedSolutions_; }
    long long solutionCount() const { return solutionCount_; }
    const SolveStatistics &statistics() const { return stats_out_; }

private:
    int n_;
    const CompatibilityData &compat_;
    std::array<int, 5> discrepancy_;
    const FrequencyStats *stats_;
    long long maxSolutions_;
    int maxStoredSolutions_;
    bool useCandidateScoring_;
    bool useFrequencyScoring_;

public:
    long long heartbeatInterval = 0; // 0 disables; e.g. 5'000'000 to match solver.py's default scale
private:

    std::vector<int> grid_;               // -1 = empty, else candidate index
    std::vector<int> remainingInventory_; // indexed by typeId
    Bits fullMask_;
    Bits availableMask_;

    std::vector<std::vector<int>> storedSolutions_;
    long long solutionCount_ = 0;
    SolveStatistics stats_out_;
    std::chrono::steady_clock::time_point searchStart_;

    static inline int idx(int row, int col, int n) { return row * n + col; }

    // Domain of legal candidates for one empty position, given the
    // current grid and remaining inventory.
    Bits domainFor(int row, int col) const {
        Bits domain = fullMask_;

        if (row > 0) {
            int above = grid_[idx(row - 1, col, n_)];
            if (above != -1) domain &= compat_.below[above];
        }
        if (col < n_ - 1) {
            int rightN = grid_[idx(row, col + 1, n_)];
            if (rightN != -1) domain &= compat_.left[rightN];
        }
        if (row < n_ - 1) {
            int below = grid_[idx(row + 1, col, n_)];
            if (below != -1) domain &= compat_.above[below];
        }
        if (col > 0) {
            int leftN = grid_[idx(row, col - 1, n_)];
            if (leftN != -1) domain &= compat_.right[leftN];
        }

        domain &= availableMask_;
        return domain;
    }

    // Most-constrained-position selection. Returns false if the board
    // is full (search complete for this branch).
    bool chooseNextPosition(int &outRow, int &outCol, Bits &outDomain) const {
        bool found = false;
        int bestSize = INT32_MAX;
        int bestRow = -1, bestCol = -1;
        Bits bestDomain;

        for (int row = 0; row < n_; ++row) {
            for (int col = 0; col < n_; ++col) {
                if (grid_[idx(row, col, n_)] != -1) continue;

                Bits d = domainFor(row, col);
                int c = d.count();

                if (c == 0) {
                    outRow = row;
                    outCol = col;
                    outDomain = d;
                    return true; // dead end signalled via empty domain
                }

                if (c < bestSize) {
                    bestSize = c;
                    bestRow = row;
                    bestCol = col;
                    bestDomain = d;
                    found = true;
                    if (bestSize == 1) {
                        outRow = bestRow;
                        outCol = bestCol;
                        outDomain = bestDomain;
                        return true;
                    }
                }
            }
        }

        if (!found) return false; // board full
        outRow = bestRow;
        outCol = bestCol;
        outDomain = bestDomain;
        return true;
    }

    std::optional<std::array<int, 4>> completedJunction(int row, int col) const {
        if (row == 0 || col == 0) return std::nullopt;
        int a = grid_[idx(row - 1, col - 1, n_)];
        int b = grid_[idx(row - 1, col, n_)];
        int c = grid_[idx(row, col - 1, n_)];
        int d = grid_[idx(row, col, n_)];
        if (a == -1 || b == -1 || c == -1 || d == -1) return std::nullopt;
        return std::array<int, 4>{
            compat_.candidates[a].corners[2],
            compat_.candidates[b].corners[3],
            compat_.candidates[d].corners[0],
            compat_.candidates[c].corners[1],
        };
    }

    double learnedJunctionScore(int row, int col) const {
        if (!useFrequencyScoring_) return 0.0;
        double score = 0.0;
        int positions[4][2] = {{row, col}, {row, col + 1}, {row + 1, col}, {row + 1, col + 1}};
        for (auto &p : positions) {
            int br = p[0], bc = p[1];
            if (!(br >= 1 && br < n_ && bc >= 1 && bc < n_)) continue;
            auto junction = completedJunction(br, bc);
            if (!junction) continue;
            auto it = stats_->junctionFrequency.find(junctionKey(*junction));
            if (it != stats_->junctionFrequency.end()) score += static_cast<double>(it->second);
        }
        return score;
    }

    double learnedNeighborScore(int row, int col, int candidateIdx) const {
        if (!useFrequencyScoring_) return 0.0;
        std::string candidateValue = edgesKey(compat_.candidates[candidateIdx].edges);

        std::string topValue;
        if (row > 0) {
            int t = grid_[idx(row - 1, col, n_)];
            topValue = (t == -1) ? "EMPTY" : edgesKey(compat_.candidates[t].edges);
        } else {
            topValue = "BOUNDARY";
        }

        std::string leftValue;
        if (col > 0) {
            int l = grid_[idx(row, col - 1, n_)];
            leftValue = (l == -1) ? "EMPTY" : edgesKey(compat_.candidates[l].edges);
        } else {
            leftValue = "BOUNDARY";
        }

        std::string key = "top=" + topValue + "|left=" + leftValue + "|candidate=" + candidateValue;
        auto it = stats_->neighborCandidateFrequency.find(key);
        return (it != stats_->neighborCandidateFrequency.end()) ? static_cast<double>(it->second) : 0.0;
    }

    // Mirrors solver.py's candidate_search_score(): temporarily places
    // the candidate to measure newly completed junctions, then undoes it.
    double candidateSearchScore(int row, int col, int candidateIdx) {
        const Candidate &cand = compat_.candidates[candidateIdx];

        double baseScore = boundaryRotationScore(cand.edges, row, col, n_, discrepancy_) +
                            positionTypeScore(cand.edges, row, col, n_, discrepancy_);

        if (stats_ != nullptr) {
            baseScore += 5.0 * cornerFrequencyScore(cand.corners, row, col, n_, *stats_);
        }

        double rarityScore = compat_.rarity[candidateIdx];

        double neighborScore = learnedNeighborScore(row, col, candidateIdx);

        if (!useFrequencyScoring_) {
            return baseScore + 2.0 * rarityScore;
        }

        int position = idx(row, col, n_);
        int savedType = cand.typeId;
        grid_[position] = candidateIdx;
        remainingInventory_[savedType] -= 1;

        double junctionScore = learnedJunctionScore(row, col);

        remainingInventory_[savedType] += 1;
        grid_[position] = -1;

        return baseScore + 2.0 * rarityScore + 1.0 * neighborScore + 0.25 * junctionScore;
    }

    // Returns true when the search should stop entirely (solution limit hit).
    bool search() {
        stats_out_.recursiveCalls++;

        if (heartbeatInterval > 0 && stats_out_.recursiveCalls % heartbeatInterval == 0) {
            double elapsed = std::chrono::duration<double>(
                                  std::chrono::steady_clock::now() - searchStart_)
                                  .count();
            std::cerr << "Still searching | time: " << elapsed << "s | calls: "
                      << stats_out_.recursiveCalls << " | solutions: " << solutionCount_
                      << " | attempts: " << stats_out_.candidateAttempts << "\n";
        }

        int row, col;

        Bits domain;
        bool hasPosition = chooseNextPosition(row, col, domain);

        if (!hasPosition) {
            // Board full: one complete solution.
            solutionCount_++;

            if (static_cast<int>(storedSolutions_.size()) < maxStoredSolutions_) {
                storedSolutions_.push_back(grid_);
            }

            if (solutionCount_ >= maxSolutions_) {
                stats_out_.stoppedAtSolutionLimit = true;
                return true;
            }
            return false;
        }

        if (domain.count() == 0) {
            stats_out_.deadEnds++;
            return false;
        }

        std::vector<int> candidateList;
        domain.forEach([&](size_t i) { candidateList.push_back(static_cast<int>(i)); });

        if (useCandidateScoring_) {
            std::vector<std::pair<double, int>> scored;
            scored.reserve(candidateList.size());
            for (int c : candidateList) scored.emplace_back(candidateSearchScore(row, col, c), c);

            std::sort(scored.begin(), scored.end(), [](const auto &a, const auto &b) {
                if (a.first != b.first) return a.first > b.first; // descending score
                return a.second < b.second;                        // stable, arbitrary tie-break
            });

            candidateList.clear();
            for (auto &sc : scored) candidateList.push_back(sc.second);
        }

        int position = idx(row, col, n_);
        bool foundValidPlacement = false;

        for (int candidateIdx : candidateList) {
            stats_out_.candidateAttempts++;

            int typeId = compat_.candidates[candidateIdx].typeId;
            if (remainingInventory_[typeId] <= 0) continue;

            // Place candidate.
            grid_[position] = candidateIdx;
            remainingInventory_[typeId] -= 1;
            bool typeExhausted = remainingInventory_[typeId] == 0;
            if (typeExhausted) availableMask_.andNot(compat_.typeMask[typeId]);

            foundValidPlacement = true; // domain already guarantees local edge validity
            stats_out_.placementsAccepted++;

            bool shouldStop = search();

            // Undo candidate.
            if (typeExhausted) availableMask_ |= compat_.typeMask[typeId];
            remainingInventory_[typeId] += 1;
            grid_[position] = -1;

            stats_out_.backtracks++;

            if (shouldStop) return true;
        }

        if (!foundValidPlacement) stats_out_.deadEnds++;
        return false;
    }
};
