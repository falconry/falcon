"""Mapping classes."""

import abc


class HTTPHeadersMapping(dict):
    """Abstract class for setting HTTP headers"""

    @abc.abstractmethod
    def items(self):
        """Preparing HTTP header keys/values

        Returns:
            list: Prepared list of tuples with HTTP header keys/values.
        """
        pass
