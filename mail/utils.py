"""
General bootcamp utility functions
"""

from itertools import islice

from odl_video import logging

log = logging.getLogger(__name__)


def chunks(iterable, chunk_size=20):
    """
    Yields chunks of an iterable as sub lists each of max size chunk_size.

    Args:
        iterable (iterable): iterable of elements to chunk
        chunk_size (int): Max size of each sublist

    Yields:
        list: List containing a slice of list_to_chunk
    """  # noqa: D401
    chunk_size = max(1, chunk_size)
    iterable = iter(iterable)
    chunk = list(islice(iterable, chunk_size))

    while chunk:  # this means its len is > 0
        yield chunk
        chunk = list(islice(iterable, chunk_size))
