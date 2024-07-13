"""Time and date utilities.

This module provides utility functions and classes for dealing with
times and dates. These functions are hoisted into the `falcon` module
for convenience::

    import falcon

    tz = falcon.TimezoneGMT()
"""

import datetime
from typing import Optional


__all__ = ['TimezoneGMT']


class TimezoneGMT(datetime.tzinfo):
    """GMT timezone class implementing the :py:class:`datetime.tzinfo` interface."""

    GMT_ZERO = datetime.timedelta(hours=0)

    def utcoffset(self, dt: Optional[datetime.datetime]) -> datetime.timedelta:
        """Get the offset from UTC.

        Args:
            dt(datetime.datetime): Ignored

        Returns:
            datetime.timedelta: GMT offset, which is equivalent to UTC and
            so is always 0.
        """

        return self.GMT_ZERO

    def tzname(self, dt: Optional[datetime.datetime]) -> str:
        """Get the name of this timezone.

        Args:
            dt(datetime.datetime): Ignored

        Returns:
            str: "GMT"
        """

        return 'GMT'

    def dst(self, dt: Optional[datetime.datetime]) -> datetime.timedelta:
        """Return the daylight saving time (DST) adjustment.

        Args:
            dt(datetime.datetime): Ignored

        Returns:
            datetime.timedelta: DST adjustment for GMT, which is always 0.
        """

        return self.GMT_ZERO
