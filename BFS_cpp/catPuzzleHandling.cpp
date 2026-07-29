#include "catPuzzleHandling.hpp"

#include <algorithm>
#include <bitset>
#include <fstream>
#include <limits>
#include <regex>
#include <stdexcept>
#include <unordered_set>

namespace catPuzzleHandling {

namespace {
constexpr std::uint8_t NIBBLE_MASK = 0x0F;

bool nibble_matches(std::uint8_t required, std::uint8_t actual) noexcept {
    // Zero is a boundary marker, not a real edge value.
    return required == 0 || required == actual;
}

std::pair<std::size_t, std::size_t> parse_dimensions(
    const std::filesystem::path& path
) {
    const std::string filename = path.filename().string();
    const std::regex pattern(R"(_(\d+)x(\d+)_(\d+))");
    std::smatch match;

    if (!std::regex_search(filename, match, pattern)) {
        throw std::runtime_error(
            "Filename must contain '_NxN_numPuzzles', for example "
            "'cats_10x10_25.txt'."
        );
    }

    const std::size_t rows = std::stoull(match[1].str());
    const std::size_t cols = std::stoull(match[2].str());
    const std::size_t num_puzzles = std::stoull(match[3].str());

    if (rows == 0 || rows != cols || num_puzzles == 0) {
        throw std::runtime_error(
            "The file must describe at least one nonempty square puzzle."
        );
    }

    return {rows, num_puzzles};
}
} // namespace

Board::Board(std::size_t n)
    : n_(n), cells_(n * n, PackedPiece{0}) {}

std::size_t Board::size() const noexcept {
    return n_;
}

bool Board::empty() const noexcept {
    return cells_.empty();
}

PackedPiece& Board::operator()(std::size_t row, std::size_t col) noexcept {
    return cells_[row * n_ + col];
}

const PackedPiece& Board::operator()(std::size_t row, std::size_t col) const noexcept {
    return cells_[row * n_ + col];
}

const std::vector<PackedPiece>& Board::data() const noexcept {
    return cells_;
}

std::vector<PackedPiece>& Board::data() noexcept {
    return cells_;
}

PuzzleData load_puzzles(const std::filesystem::path& file_path) {
    const auto [n, num_puzzles] = parse_dimensions(file_path);

    std::ifstream input(file_path);
    if (!input) {
        throw std::runtime_error("Could not open puzzle file: " + file_path.string());
    }

    const std::size_t total_pieces = num_puzzles * n * n;
    const std::size_t total_edges = total_pieces * 4;

    std::vector<int> values;
    values.reserve(total_edges);

    int value = 0;
    while (input >> value) {
        values.push_back(value);
    }

    if (values.size() != total_edges) {
        throw std::runtime_error(
            "Expected " + std::to_string(total_edges) +
            " edge integers, but read " + std::to_string(values.size()) + "."
        );
    }

    PuzzleData result;
    result.n = n;
    result.puzzles.resize(num_puzzles);

    std::size_t cursor = 0;
    for (RawPuzzle& puzzle : result.puzzles) {
        puzzle.resize(n * n);

        for (RawPiece& piece : puzzle) {
            for (std::int8_t& edge : piece) {
                const int raw = values[cursor++];
                if (raw == 0 || raw < -4 || raw > 4) {
                    throw std::runtime_error(
                        "Every edge must be one of -4..-1 or 1..4."
                    );
                }
                edge = static_cast<std::int8_t>(raw);
            }
        }
    }

    return result;
}

std::uint8_t edge_to_bit(int edge) {
    switch (edge) {
        case -1: return 0b1000;
        case -2: return 0b0100;
        case -3: return 0b0010;
        case -4: return 0b0001;
        case +1: return 0b0111;
        case +2: return 0b1011;
        case +3: return 0b1101;
        case +4: return 0b1110;
        default:
            throw std::invalid_argument("Edge must be one of -4..-1 or 1..4.");
    }
}

std::int8_t bit_to_edge(std::uint8_t nibble) {
    switch (nibble & NIBBLE_MASK) {
        case 0b1000: return -1;
        case 0b0100: return -2;
        case 0b0010: return -3;
        case 0b0001: return -4;
        case 0b0111: return +1;
        case 0b1011: return +2;
        case 0b1101: return +3;
        case 0b1110: return +4;
        default:
            throw std::invalid_argument("Nibble is not a valid encoded edge.");
    }
}

PackedPiece piece_to_bits(const RawPiece& piece) {
    const PackedPiece top = edge_to_bit(piece[0]);
    const PackedPiece right = edge_to_bit(piece[1]);
    const PackedPiece bottom = edge_to_bit(piece[2]);
    const PackedPiece left = edge_to_bit(piece[3]);

    // Printed order: [Top][Right][Bottom][Left].
    return static_cast<PackedPiece>(
        (top << 12) |
        (right << 8) |
        (bottom << 4) |
        left
    );
}

RawPiece bits_to_piece(PackedPiece packed_piece) {
    return RawPiece{
        bit_to_edge(static_cast<std::uint8_t>((packed_piece >> 12) & NIBBLE_MASK)),
        bit_to_edge(static_cast<std::uint8_t>((packed_piece >> 8) & NIBBLE_MASK)),
        bit_to_edge(static_cast<std::uint8_t>((packed_piece >> 4) & NIBBLE_MASK)),
        bit_to_edge(static_cast<std::uint8_t>(packed_piece & NIBBLE_MASK))
    };
}

std::vector<PackedPiece> board_to_bits_vector(const RawPuzzle& board) {
    std::vector<PackedPiece> vector_1d;
    vector_1d.reserve(board.size());

    for (const RawPiece& piece : board) {
        vector_1d.push_back(piece_to_bits(piece));
    }

    return vector_1d;
}

RawPuzzle bits_vector_to_board(
    const std::vector<PackedPiece>& vector_1d,
    std::size_t n
) {
    if (vector_1d.size() != n * n) {
        throw std::invalid_argument("Packed vector size must equal n*n.");
    }

    RawPuzzle board;
    board.reserve(vector_1d.size());

    for (PackedPiece piece : vector_1d) {
        board.push_back(bits_to_piece(piece));
    }

    return board;
}

PackedPiece rotate_piece(PackedPiece piece, std::uint8_t clockwise_turns) noexcept {
    const std::uint8_t turns = static_cast<std::uint8_t>(clockwise_turns & 0x03U);
    if (turns == 0) {
        return piece;
    }

    const unsigned shift = 4U * turns;
    const std::uint32_t value = piece;

    // [T][R][B][L] --clockwise--> [L][T][R][B].
    return static_cast<PackedPiece>(
        ((value >> shift) | (value << (16U - shift))) & 0xFFFFU
    );
}

std::vector<std::pair<std::size_t, std::size_t>> diagonal_coordinates(
    std::size_t n,
    std::size_t layer
) {
    if (n == 0 || layer > 2 * n - 2) {
        throw std::out_of_range("Diagonal layer is outside the board.");
    }

    const std::size_t min_col = layer >= n ? layer - n + 1 : 0;
    const std::size_t max_col = std::min(layer, n - 1);

    std::vector<std::pair<std::size_t, std::size_t>> coordinates;
    coordinates.reserve(max_col - min_col + 1);

    for (std::size_t col = min_col; col <= max_col; ++col) {
        coordinates.emplace_back(layer - col, col);
    }

    return coordinates;
}

std::vector<TargetCorner> transcribe_sides(
    const Board& solvingBoard,
    std::size_t layer
) {
    const std::size_t n = solvingBoard.size();
    if (n == 0 || layer > 2 * n - 2) {
        throw std::out_of_range("Layer is outside the solving board.");
    }

    const auto coordinates = diagonal_coordinates(n, layer);
    std::vector<std::uint8_t> inverse_right;
    std::vector<std::uint8_t> inverse_bottom;
    inverse_right.reserve(coordinates.size());
    inverse_bottom.reserve(coordinates.size());

    for (const auto& [row, col] : coordinates) {
        const PackedPiece piece = solvingBoard(row, col);
        if (piece == 0) {
            throw std::logic_error(
                "transcribe_sides received an incomplete current layer."
            );
        }

        const auto right = static_cast<std::uint8_t>((piece >> 8) & NIBBLE_MASK);
        const auto bottom = static_cast<std::uint8_t>((piece >> 4) & NIBBLE_MASK);

        inverse_right.push_back(static_cast<std::uint8_t>(right ^ NIBBLE_MASK));
        inverse_bottom.push_back(static_cast<std::uint8_t>(bottom ^ NIBBLE_MASK));
    }

    std::vector<TargetCorner> output;

    // The next diagonal grows only while the current layer is below n - 1.
    // At layer n - 1, the current diagonal is already full length and the next
    // diagonal shrinks, so the two boundary-only entries must disappear.
    if (layer < n - 1) {
        output.reserve(coordinates.size() + 1);
        output.push_back(inverse_right.front()); // [0000][required left]

        for (std::size_t i = 0; i + 1 < coordinates.size(); ++i) {
            output.push_back(static_cast<TargetCorner>(
                (inverse_bottom[i] << 4) | inverse_right[i + 1]
            ));
        }

        output.push_back(static_cast<TargetCorner>(
            inverse_bottom.back() << 4
        )); // [required top][0000]
    } else {
        if (coordinates.size() > 1) {
            output.reserve(coordinates.size() - 1);
        }

        for (std::size_t i = 0; i + 1 < coordinates.size(); ++i) {
            output.push_back(static_cast<TargetCorner>(
                (inverse_bottom[i] << 4) | inverse_right[i + 1]
            ));
        }
    }

    return output;
}

std::vector<MatchResult> find_all_matching_pieces(
    TargetCorner target_corner,
    const std::vector<PackedPiece>& available_pieces_1d,
    std::uint64_t* tries
) {
    const auto target_top = static_cast<std::uint8_t>((target_corner >> 4) & NIBBLE_MASK);
    const auto target_left = static_cast<std::uint8_t>(target_corner & NIBBLE_MASK);

    std::vector<MatchResult> matches;
    matches.reserve(available_pieces_1d.size());

    for (std::size_t index = 0; index < available_pieces_1d.size(); ++index) {
        const PackedPiece original = available_pieces_1d[index];

        // Avoid returning the same orientation more than once for symmetric pieces.
        std::array<PackedPiece, 4> seen{};
        std::size_t seen_count = 0;

        for (std::uint8_t rotation = 0; rotation < 4; ++rotation) {
            if (tries != nullptr) {
                ++(*tries);
            }

            const PackedPiece rotated = rotate_piece(original, rotation);

            bool duplicate_rotation = false;
            for (std::size_t s = 0; s < seen_count; ++s) {
                if (seen[s] == rotated) {
                    duplicate_rotation = true;
                    break;
                }
            }
            if (duplicate_rotation) {
                continue;
            }
            seen[seen_count++] = rotated;

            const auto top = static_cast<std::uint8_t>((rotated >> 12) & NIBBLE_MASK);
            const auto left = static_cast<std::uint8_t>(rotated & NIBBLE_MASK);

            if (nibble_matches(target_top, top) &&
                nibble_matches(target_left, left)) {
                matches.push_back(MatchResult{index, rotated, rotation});
            }
        }
    }

    return matches;
}

std::optional<MatchResult> find_matching_piece(
    TargetCorner target_corner,
    const std::vector<PackedPiece>& available_pieces_1d,
    std::uint64_t* tries
) {
    const auto target_top = static_cast<std::uint8_t>((target_corner >> 4) & NIBBLE_MASK);
    const auto target_left = static_cast<std::uint8_t>(target_corner & NIBBLE_MASK);

    for (std::size_t index = 0; index < available_pieces_1d.size(); ++index) {
        const PackedPiece original = available_pieces_1d[index];
        std::array<PackedPiece, 4> seen{};
        std::size_t seen_count = 0;

        for (std::uint8_t rotation = 0; rotation < 4; ++rotation) {
            if (tries != nullptr) {
                ++(*tries);
            }

            const PackedPiece rotated = rotate_piece(original, rotation);

            bool duplicate_rotation = false;
            for (std::size_t s = 0; s < seen_count; ++s) {
                if (seen[s] == rotated) {
                    duplicate_rotation = true;
                    break;
                }
            }
            if (duplicate_rotation) {
                continue;
            }
            seen[seen_count++] = rotated;

            const auto top = static_cast<std::uint8_t>((rotated >> 12) & NIBBLE_MASK);
            const auto left = static_cast<std::uint8_t>(rotated & NIBBLE_MASK);

            if (nibble_matches(target_top, top) &&
                nibble_matches(target_left, left)) {
                return MatchResult{index, rotated, rotation};
            }
        }
    }

    return std::nullopt;
}

void swap_pop(
    std::vector<PackedPiece>& available_pieces,
    std::size_t index
) {
    if (index >= available_pieces.size()) {
        throw std::out_of_range("swap_pop index is outside the piece pool.");
    }

    available_pieces[index] = available_pieces.back();
    available_pieces.pop_back();
}

void fossilize(
    FossilizedCase& case_history,
    const std::vector<std::uint32_t>& layer_piece_indices,
    const std::vector<std::uint8_t>& layer_rotations
) {
    if (layer_piece_indices.size() != layer_rotations.size()) {
        throw std::invalid_argument(
            "Piece-index and rotation vectors must have the same length."
        );
    }

    FossilizedLayer layer;
    layer.reserve(layer_piece_indices.size());

    for (std::size_t i = 0; i < layer_piece_indices.size(); ++i) {
        if (layer_rotations[i] > 3) {
            throw std::invalid_argument("Rotation must be 0, 1, 2, or 3.");
        }
        layer.push_back(FossilizedPiece{
            layer_piece_indices[i],
            layer_rotations[i]
        });
    }

    case_history.push_back(std::move(layer));
}

std::string to_binary(PackedPiece piece) {
    return std::bitset<16>(piece).to_string();
}

std::string to_binary(TargetCorner corner) {
    return std::bitset<8>(corner).to_string();
}

} // namespace catPuzzleHandling
