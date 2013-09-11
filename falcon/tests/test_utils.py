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

    def test_http_date_to_dt(self):
        self.assertEquals(
            falcon.http_date_to_dt('Thu, 04 Apr 2013 00:00:00 GMT'),
            datetime(2013, 4, 4))

        self.assertEquals(
            falcon.http_date_to_dt('Thu, 04 Apr 2013 10:28:54 GMT'),
            datetime(2013, 4, 4, 10, 28, 54))

    def test_pack_query_params_none(self):
        self.assertEquals(
            falcon.to_query_str({}),
            '')

    def test_pack_query_params_one(self):
        self.assertEquals(
            falcon.to_query_str({'limit': 10}),
            '?limit=10')

        self.assertEquals(
            falcon.to_query_str({'things': [1, 2, 3]}),
            '?things=1,2,3')

        self.assertEquals(
            falcon.to_query_str({'things': ['a']}),
            '?things=a')

        self.assertEquals(
            falcon.to_query_str({'things': ['a', 'b']}),
            '?things=a,b')

    def test_pack_query_params_several(self):
        garbage_in = {
            'limit': 17,
            'echo': True,
            'doit': False,
            'x': 'val',
            'y': 0.2
        }

        query_str = falcon.to_query_str(garbage_in)
        fields = query_str[1:].split('&')

        garbage_out = {}
        for field in fields:
            k, v = field.split('=')
            garbage_out[k] = v

        expected = {
            'echo': 'true',
            'limit': '17',
            'x': 'val',
            'y': '0.2',
            'doit': 'false'}

        self.assertEquals(expected, garbage_out)

    def test_percent_escape(self):
        url = 'http://example.com/v1/fizbit/messages?limit=3&echo=true'
        self.assertEquals(falcon.percent_escape(url), url)

        url2a = u'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        url2b = 'http://example.com/v1/fizbit/messages?limit=3&e%C3%A7ho=true'
        self.assertEquals(falcon.percent_escape(url2a), url2b)
