#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace catPuzzleHandling {

using PackedPiece = std::uint16_t;
using TargetCorner = std::uint8_t;

// Raw edge order is always: top, right, bottom, left.
using RawPiece = std::array<std::int8_t, 4>;
using RawPuzzle = std::vector<RawPiece>;

struct PuzzleData {
    std::size_t n = 0;
    std::vector<RawPuzzle> puzzles;
};

// A board is logically n x n, but cells are contiguous for cache efficiency.
class Board {
public:
    explicit Board(std::size_t n = 0);

    [[nodiscard]] std::size_t size() const noexcept;
    [[nodiscard]] bool empty() const noexcept;

    PackedPiece& operator()(std::size_t row, std::size_t col) noexcept;
    const PackedPiece& operator()(std::size_t row, std::size_t col) const noexcept;

    [[nodiscard]] const std::vector<PackedPiece>& data() const noexcept;
    [[nodiscard]] std::vector<PackedPiece>& data() noexcept;

private:
    std::size_t n_ = 0;
    std::vector<PackedPiece> cells_;
};

struct MatchResult {
    std::size_t index = 0;
    PackedPiece matching_piece = 0;
    std::uint8_t rotation = 0; // clockwise quarter turns: 0, 1, 2, 3
};

struct FossilizedPiece {
    std::uint32_t original_index = 0;
    std::uint8_t rotation = 0;
};

using FossilizedLayer = std::vector<FossilizedPiece>;
using FossilizedCase = std::vector<FossilizedLayer>;

// File name is expected to contain: _NxN_numPuzzles
// Example: cats_10x10_25.txt
PuzzleData load_puzzles(const std::filesystem::path& file_path);

std::uint8_t edge_to_bit(int edge);
std::int8_t bit_to_edge(std::uint8_t nibble);

PackedPiece piece_to_bits(const RawPiece& piece);
RawPiece bits_to_piece(PackedPiece packed_piece);

std::vector<PackedPiece> board_to_bits_vector(const RawPuzzle& board);
RawPuzzle bits_vector_to_board(
    const std::vector<PackedPiece>& vector_1d,
    std::size_t n
);

PackedPiece rotate_piece(PackedPiece piece, std::uint8_t clockwise_turns = 1) noexcept;

// Returns coordinates on a diagonal in this order:
// (layer, 0), (layer - 1, 1), ... after clipping to the board.
std::vector<std::pair<std::size_t, std::size_t>> diagonal_coordinates(
    std::size_t n,
    std::size_t layer
);

// Returns target bytes for the next diagonal.
// High nibble = required top; low nibble = required left.
// A zero nibble means that side has no neighbor and is unconstrained.
std::vector<TargetCorner> transcribe_sides(
    const Board& solvingBoard,
    std::size_t layer
);

// Exact Python-style first-match function.
std::optional<MatchResult> find_matching_piece(
    TargetCorner target_corner,
    const std::vector<PackedPiece>& available_pieces_1d,
    std::uint64_t* tries = nullptr
);

// Needed by a real BFS: returns every piece/orientation that fits.
// Symmetric duplicate rotations of the same physical piece are omitted.
std::vector<MatchResult> find_all_matching_pieces(
    TargetCorner target_corner,
    const std::vector<PackedPiece>& available_pieces_1d,
    std::uint64_t* tries = nullptr
);

// O(1) removal when order does not matter.
void swap_pop(
    std::vector<PackedPiece>& available_pieces,
    std::size_t index
);

// Appends one completed layer's original indices and rotations to a case.
void fossilize(
    FossilizedCase& case_history,
    const std::vector<std::uint32_t>& layer_piece_indices,
    const std::vector<std::uint8_t>& layer_rotations
);

std::string to_binary(PackedPiece piece);
std::string to_binary(TargetCorner corner);

} // namespace catPuzzleHandling
