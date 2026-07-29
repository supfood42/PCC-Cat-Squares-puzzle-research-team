#include "catPuzzleHandling.hpp"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace surgeon = catPuzzleHandling;

namespace {

struct Case {
    surgeon::Board solvingBoard;
    std::vector<surgeon::PackedPiece> availablePieces;
};

struct SearchStats {
    std::uint64_t tries = 0;
    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    std::chrono::steady_clock::time_point next_report = start + std::chrono::seconds(10);

    void report_if_due(std::size_t active_cases, std::size_t layer) {
        const auto now = std::chrono::steady_clock::now();
        if (now < next_report) {
            return;
        }

        const double seconds = std::chrono::duration<double>(now - start).count();
        std::cout << "[" << std::fixed << std::setprecision(1) << seconds
                  << " s] tries=" << tries
                  << ", active cases=" << active_cases
                  << ", layer=" << layer << '\n';

        do {
            next_report += std::chrono::seconds(10);
        } while (next_report <= now);
    }
};

void print_solution(const surgeon::Board& board) {
    const std::size_t n = board.size();

    std::cout << "\nPacked solution ([Top][Right][Bottom][Left]):\n";
    for (std::size_t row = 0; row < n; ++row) {
        for (std::size_t col = 0; col < n; ++col) {
            std::cout << surgeon::to_binary(board(row, col)) << ' ';
        }
        std::cout << '\n';
    }

    std::cout << "\nSigned edge solution (top right bottom left):\n";
    for (std::size_t row = 0; row < n; ++row) {
        for (std::size_t col = 0; col < n; ++col) {
            const surgeon::RawPiece piece = surgeon::bits_to_piece(board(row, col));
            std::cout << '['
                      << static_cast<int>(piece[0]) << ' '
                      << static_cast<int>(piece[1]) << ' '
                      << static_cast<int>(piece[2]) << ' '
                      << static_cast<int>(piece[3]) << "] ";
        }
        std::cout << '\n';
    }
}

// Layer-by-layer BFS matching the Python control flow.
// Returns the first completed case, while retaining all valid cases at each depth.
std::optional<Case> solve_bfs(
    const std::vector<surgeon::PackedPiece>& vectored_board,
    std::size_t n,
    std::mt19937_64& rng,
    std::size_t max_cases,
    SearchStats& stats
) {
    if (vectored_board.empty()) {
        return std::nullopt;
    }

    std::vector<surgeon::PackedPiece> availablePieces = vectored_board;
    surgeon::Board solvingBoard(n);

    std::uniform_int_distribution<std::size_t> starter_distribution(
        0,
        availablePieces.size() - 1
    );

    const std::size_t starter_idx = starter_distribution(rng);
    solvingBoard(0, 0) = availablePieces[starter_idx];
    surgeon::swap_pop(availablePieces, starter_idx);

    std::vector<Case> cases;
    cases.push_back(Case{std::move(solvingBoard), std::move(availablePieces)});

    if (n == 1) {
        return cases.front();
    }

    // Current layer runs from 0 through 2*n-3. Each iteration fills layer+1.
    for (std::size_t layer = 0; layer < 2 * n - 2; ++layer) {
        std::vector<Case> next_cases;

        for (const Case& current_case : cases) {
            const std::vector<surgeon::TargetCorner> matching_sides =
                surgeon::transcribe_sides(current_case.solvingBoard, layer);

            const auto positions = surgeon::diagonal_coordinates(n, layer + 1);
            if (matching_sides.size() != positions.size()) {
                throw std::logic_error(
                    "transcribe_sides output does not match the next diagonal size."
                );
            }

            // Populate one diagonal corner at a time. This inner list represents
            // all partial branches for this one incoming case.
            std::vector<Case> partial_cases;
            partial_cases.push_back(current_case);

            for (std::size_t corner_index = 0;
                 corner_index < matching_sides.size();
                 ++corner_index) {
                const auto [row, col] = positions[corner_index];
                const surgeon::TargetCorner corner = matching_sides[corner_index];

                std::vector<Case> expanded_cases;

                for (const Case& partial_case : partial_cases) {
                    const auto matches = surgeon::find_all_matching_pieces(
                        corner,
                        partial_case.availablePieces,
                        &stats.tries
                    );

                    // Every match creates an independent BFS branch.
                    expanded_cases.reserve(expanded_cases.size() + matches.size());
                    for (const surgeon::MatchResult& match : matches) {
                        Case child = partial_case;
                        child.solvingBoard(row, col) = match.matching_piece;
                        surgeon::swap_pop(child.availablePieces, match.index);
                        expanded_cases.push_back(std::move(child));

                        if (max_cases != 0 && expanded_cases.size() > max_cases) {
                            throw std::runtime_error(
                                "BFS case limit exceeded while populating a layer."
                            );
                        }
                    }
                }

                partial_cases = std::move(expanded_cases);
                if (partial_cases.empty()) {
                    break; // This incoming case has no valid continuation.
                }

                stats.report_if_due(partial_cases.size(), layer + 1);
            }

            if (!partial_cases.empty()) {
                if (max_cases != 0 &&
                    next_cases.size() + partial_cases.size() > max_cases) {
                    throw std::runtime_error(
                        "BFS case limit exceeded. Increase the limit or use DFS."
                    );
                }

                for (Case& completed_layer_case : partial_cases) {
                    next_cases.push_back(std::move(completed_layer_case));
                }
            }
        }

        cases = std::move(next_cases);

        std::cout << "Completed diagonal " << (layer + 1)
                  << ": " << cases.size() << " active case(s)\n";

        if (cases.empty()) {
            return std::nullopt;
        }
    }

    return std::move(cases.front());
}

std::size_t parse_size_argument(const char* text, const char* name) {
    try {
        const unsigned long long value = std::stoull(text);
        if (value > std::numeric_limits<std::size_t>::max()) {
            throw std::out_of_range("too large");
        }
        return static_cast<std::size_t>(value);
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("Invalid ") + name + ": " + text);
    }
}

} // namespace

int main(int argc, char* argv[]) {
    try {
        if (argc < 2 || argc > 4) {
            std::cerr
                << "Usage: puzzle_solve_BFS <puzzle_file> [seed] [max_cases]\n"
                << "  max_cases=0 means unlimited (default).\n";
            return EXIT_FAILURE;
        }

        const std::filesystem::path file_path = argv[1];
        const std::uint64_t seed = argc >= 3
            ? static_cast<std::uint64_t>(parse_size_argument(argv[2], "seed"))
            : std::random_device{}();
        const std::size_t max_cases = argc >= 4
            ? parse_size_argument(argv[3], "max_cases")
            : 0;

        const surgeon::PuzzleData puzzleData = surgeon::load_puzzles(file_path);
        std::mt19937_64 rng(seed);

        std::cout << "Loaded " << puzzleData.puzzles.size()
                  << " puzzle(s) of size " << puzzleData.n << 'x'
                  << puzzleData.n << ".\n"
                  << "Random seed: " << seed << "\n";

        for (std::size_t i = 0; i < puzzleData.puzzles.size(); ++i) {
            std::cout << "\nSolving puzzle " << (i + 1) << "...\n";

            const std::vector<surgeon::PackedPiece> vectored_board =
                surgeon::board_to_bits_vector(puzzleData.puzzles[i]);

            SearchStats stats;
            const auto solution = solve_bfs(
                vectored_board,
                puzzleData.n,
                rng,
                max_cases,
                stats
            );

            const double elapsed = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - stats.start
            ).count();

            if (solution.has_value()) {
                std::cout << "Solved puzzle " << (i + 1) << ".\n";
                print_solution(solution->solvingBoard);
            } else {
                std::cout << "No solution found for puzzle " << (i + 1)
                          << " with the selected starter piece.\n";
            }

            std::cout << "Tries: " << stats.tries << '\n'
                      << "Time: " << std::fixed << std::setprecision(3)
                      << elapsed << " seconds\n";
        }

        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
