import random

from pecan import expose, response, request


def rand_string(min, max):
    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord('\t'), ord('~')))
                    for i in range(string_length)])


body = rand_string(10240, 10240)


class TestController(object):
    def __init__(self, account_id):
        self.account_id = account_id

    @expose(content_type='text/plain')
    def test(self):
        user_agent = request.headers['User-Agent']  # NOQA
        limit = request.params['limit']  # NOQA
        response.headers['X-Test'] = 'Funky Chicken'

        return body


class HelloController(object):
    @expose()
    def _lookup(self, account_id, *remainder):
        return TestController(account_id), remainder


class RootController(object):

    @expose(content_type='text/plain')
    def index(self):
        response.headers['X-Test'] = 'Funky Chicken'
        return body

    hello = HelloController()
