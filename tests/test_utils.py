"""Tests for utility functions."""

import pytest

from src.utils.helpers import get_code_line, get_code_context, Timer, chunk_list


SAMPLE_CODE = """#include <stdio.h>
int main() {
    int x = 10;
    int y = 20;
    printf("%d", x + y);
    return 0;
}"""


class TestGetCodeLine:
    def test_valid_line(self):
        assert get_code_line(SAMPLE_CODE, 3) == "int x = 10;"

    def test_first_line(self):
        assert get_code_line(SAMPLE_CODE, 1) == "#include <stdio.h>"

    def test_out_of_range(self):
        result = get_code_line(SAMPLE_CODE, 100)
        assert result == ""

    def test_zero_line(self):
        # Line 0 should return line 1 (clamped to 0 index)
        result = get_code_line(SAMPLE_CODE, 0)
        assert result == "#include <stdio.h>"


class TestGetCodeContext:
    def test_context_around_line(self):
        ctx = get_code_context(SAMPLE_CODE, 4, context_lines=1)
        assert ">>" in ctx  # Should mark the target line
        assert "int y = 20;" in ctx

    def test_context_at_start(self):
        ctx = get_code_context(SAMPLE_CODE, 1, context_lines=2)
        assert "#include" in ctx


class TestTimer:
    def test_timer_measures(self):
        with Timer() as t:
            total = sum(range(1000))
        assert t.elapsed_ms > 0


class TestChunkList:
    def test_even_chunks(self):
        result = list(chunk_list([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_uneven_chunks(self):
        result = list(chunk_list([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_single_chunk(self):
        result = list(chunk_list([1, 2, 3], 10))
        assert result == [[1, 2, 3]]

    def test_empty_list(self):
        result = list(chunk_list([], 5))
        assert result == []
