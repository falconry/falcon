from datetime import datetime
import testtools

import falcon


class TestFalconUtils(testtools.TestCase):

    def test_dt_to_http(self):
        self.assertEquals(
            falcon.dt_to_http(datetime(2013, 4, 4)),
            'Thu, 04 Apr 2013 00:00:00 GMT')

        self.assertEquals(
            falcon.dt_to_http(datetime(2013, 4, 4, 10, 28, 54)),
            'Thu, 04 Apr 2013 10:28:54 GMT')
