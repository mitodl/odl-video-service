"""
Tests for the utils module
"""

import unittest
from math import ceil

from mail.utils import chunks


class UtilTests(unittest.TestCase):
    """
    Tests for assorted utility functions
    """

    def test_chunks(self):
        """
        test for chunks
        """
        input_list = list(range(113))
        output_list = []
        for nums in chunks(input_list):
            output_list += nums
        assert output_list == input_list

        output_list = []
        for nums in chunks(input_list, chunk_size=1):
            output_list += nums
        assert output_list == input_list

        output_list = []
        for nums in chunks(input_list, chunk_size=124):
            output_list += nums
        assert output_list == input_list

    def test_chunks_iterable(self):
        """
        test that chunks works on non-list iterables too
        """
        count = 113
        input_range = range(count)
        chunk_output = []
        for chunk in chunks(input_range, chunk_size=10):
            chunk_output.append(chunk)
        assert len(chunk_output) == ceil(113 / 10)

        range_list = []
        for chunk in chunk_output:
            range_list += chunk
        assert range_list == list(range(count))
