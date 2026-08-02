#include "catPuzzleHandling.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace surgeon = catPuzzleHandling;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

int main() {
    const surgeon::RawPiece raw{-1, +2, -3, +4};
    const surgeon::PackedPiece packed = surgeon::piece_to_bits(raw);
    require(surgeon::bits_to_piece(packed) == raw, "pack/unpack failed");

    const auto rotated = surgeon::rotate_piece(packed, 1);
    const surgeon::RawPiece expected_rotated{+4, -1, +2, -3};
    require(
        surgeon::bits_to_piece(rotated) == expected_rotated,
        "clockwise rotation failed"
    );

    // A zero high nibble is a top-boundary wildcard.
    std::vector<surgeon::PackedPiece> pool{packed};
    const std::uint8_t required_left = static_cast<std::uint8_t>(packed & 0x0F);
    const auto wildcard_match = surgeon::find_matching_piece(required_left, pool);
    require(wildcard_match.has_value(), "boundary wildcard matching failed");

    surgeon::Board board(3);
    for (std::size_t r = 0; r < 3; ++r) {
        for (std::size_t c = 0; c < 3; ++c) {
            board(r, c) = packed;
        }
    }

    require(surgeon::transcribe_sides(board, 0).size() == 2, "layer 0 size failed");
    require(surgeon::transcribe_sides(board, 1).size() == 3, "layer 1 size failed");
    require(surgeon::transcribe_sides(board, 2).size() == 2, "layer 2 size failed");
    require(surgeon::transcribe_sides(board, 3).size() == 1, "layer 3 size failed");

    std::vector<surgeon::PackedPiece> removable{1, 2, 3, 4};
    surgeon::swap_pop(removable, 1);
    require(
        removable == std::vector<surgeon::PackedPiece>{1, 4, 3},
        "swap_pop failed"
    );

    std::cout << "All tests passed.\n";
}
