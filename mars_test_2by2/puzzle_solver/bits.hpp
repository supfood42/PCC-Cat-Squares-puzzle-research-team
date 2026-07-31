// bits.hpp
// A tiny dynamic bitset used to represent sets of candidate indices.
// This replaces Python's `set()` intersections with O(word-count)
// bitwise AND operations, which is the single biggest speed win
// over the original implementation.
#pragma once
#include <cstdint>
#include <vector>
#include <functional>

class Bits {
public:
    Bits() = default;

    explicit Bits(size_t n) : nbits_(n), words_((n + 63) / 64, 0ULL) {}

    void setAll() {
        for (auto &w : words_) w = ~0ULL;
        clearHighBits();
    }

    void clearAll() {
        for (auto &w : words_) w = 0ULL;
    }

    void set(size_t i) { words_[i >> 6] |= (1ULL << (i & 63)); }
    void reset(size_t i) { words_[i >> 6] &= ~(1ULL << (i & 63)); }
    bool test(size_t i) const { return (words_[i >> 6] >> (i & 63)) & 1ULL; }

    Bits &operator&=(const Bits &o) {
        for (size_t i = 0; i < words_.size(); ++i) words_[i] &= o.words_[i];
        return *this;
    }

    Bits &operator|=(const Bits &o) {
        for (size_t i = 0; i < words_.size(); ++i) words_[i] |= o.words_[i];
        return *this;
    }

    // Clear the bits present in `o` (set-difference, in place).
    Bits &andNot(const Bits &o) {
        for (size_t i = 0; i < words_.size(); ++i) words_[i] &= ~o.words_[i];
        return *this;
    }

    Bits operator&(const Bits &o) const {
        Bits r = *this;
        r &= o;
        return r;
    }

    bool any() const {
        for (auto w : words_)
            if (w) return true;
        return false;
    }

    int count() const {
        int c = 0;
        for (auto w : words_) c += __builtin_popcountll(w);
        return c;
    }

    size_t size() const { return nbits_; }

    // Call f(index) for every set bit, lowest to highest.
    void forEach(const std::function<void(size_t)> &f) const {
        for (size_t wi = 0; wi < words_.size(); ++wi) {
            uint64_t w = words_[wi];
            while (w) {
                unsigned b = __builtin_ctzll(w);
                f(wi * 64 + b);
                w &= (w - 1);
            }
        }
    }

private:
    void clearHighBits() {
        if (nbits_ % 64 != 0 && !words_.empty()) {
            uint64_t mask = (1ULL << (nbits_ % 64)) - 1;
            words_.back() &= mask;
        }
    }

    size_t nbits_ = 0;
    std::vector<uint64_t> words_;
};
