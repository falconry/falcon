from falcon.request import Request
import falcon.testing as testing


class TestAccessRoute(testing.TestBase):

    def test_remote_addr_only(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route',
            headers={
                'Forwarded': ('for=192.0.2.43, for="[2001:db8:cafe::17]:555",'
                              'for="unknown", by=_hidden,for="\\"\\\\",'
                              'for="198\\.51\\.100\\.17\\:1236";'
                              'proto=https;host=example.com')
            }))
        self.assertEqual(req.remote_addr, '127.0.0.1')

    def test_rfc_forwarded(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route',
            headers={
                'Forwarded': ('for=192.0.2.43, for="[2001:db8:cafe::17]:555",'
                              'for="unknown", by=_hidden,for="\\"\\\\",'
                              'for="198\\.51\\.100\\.17\\:1236";'
                              'proto=https;host=example.com')
            }))
        self.assertEqual(req.access_route,
                         ['192.0.2.43', '2001:db8:cafe::17',
                          'unknown', '"\\', '198.51.100.17'])
        # test cached
        self.assertEqual(req.access_route,
                         ['192.0.2.43', '2001:db8:cafe::17',
                          'unknown', '"\\', '198.51.100.17'])

    def test_malformed_rfc_forwarded(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route',
            headers={
                'Forwarded': 'for'
            }))
        self.assertEqual(req.access_route, ['127.0.0.1'])
        # test cached
        self.assertEqual(req.access_route, ['127.0.0.1'])

    def test_x_forwarded_for(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route',
            headers={
                'X-Forwarded-For': ('192.0.2.43, 2001:db8:cafe::17,'
                                    'unknown, _hidden, 203.0.113.60')
            }))
        self.assertEqual(req.access_route,
                         ['192.0.2.43', '2001:db8:cafe::17',
                          'unknown', '_hidden', '203.0.113.60'])

    def test_x_real_ip(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route',
            headers={
                'X-Real-IP': '2001:db8:cafe::17'
            }))
        self.assertEqual(req.access_route, ['2001:db8:cafe::17'])

    def test_remote_addr(self):
        req = Request(testing.create_environ(
            host='example.com',
            path='/access_route'))
        self.assertEqual(req.access_route, ['127.0.0.1'])
