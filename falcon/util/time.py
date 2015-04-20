import datetime


class TimezoneGMT(datetime.tzinfo):
    """Used in cookie response formatting"""

    GMT_ZERO = datetime.timedelta(hours=0)

    def utcoffset(self, dt):
        return self.GMT_ZERO

    def tzname(self, dt):
        return "GMT"

    def dst(self, dt):
        return self.GMT_ZERO
