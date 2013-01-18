import random

from pecan import expose, response


def rand_string(min, max):
    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord('\t'), ord('~')))
                    for i in range(string_length)])


body = rand_string(10240, 10240)

class HelloController(object):
    @expose(content_type='text/plain')
    def test(self):
        response.headers['X-Test'] = 'Funky Chicken'
        return body


class RootController(object):

    @expose(content_type='text/plain')
    def index(self):
        response.headers['X-Test'] = 'Funky Chicken'
        return body

    hello = HelloController()
