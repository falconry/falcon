#!/usr/bin/env python

import sys
import random
import argparse
from timeit import repeat

from create import *

sys.path.append('..')
import tests.helpers as helpers
del sys.path[-1]


def avg(array):
    return sum(array) / len(array)


def bench(name, iterations=10000):
    func = create_bench(name)
    results = repeat(func, number=iterations)

    sec_per_req = avg(results) / iterations

    sys.stdout.write('.')
    sys.stdout.flush()

    return (name, sec_per_req)


def create_bench(name):
    srmock = helpers.StartResponseMock()
    env = helpers.create_environ('/hello/584/test', query_string='limit=10')
    body = helpers.rand_string(10240, 10240)
    headers = {'X-Test': 'Funky Chicken'}

    app = eval('create_{0}(body, headers)'.format(name.lower()))

    def bench():
        app(env, srmock)

    return bench


if __name__ == '__main__':
    frameworks = [
        'Wheezy', 'Flask', 'Werkzeug', 'Falcon', 'Pecan', 'Bottle'
    ]

    parser = argparse.ArgumentParser(description="Falcon benchmark runner")
    parser.add_argument('-b', '--benchmark', type=str, action='append',
                        choices=frameworks, dest='frameworks')
    parser.add_argument('-i', '--iterations', type=int, default=10000)
    args = parser.parse_args()

    if args.frameworks:
        frameworks = args.frameworks

    random.shuffle(frameworks)

    sys.stdout.write('\nBenchmarking')
    sys.stdout.flush()
    results = [bench(framework, args.iterations) for framework in frameworks]
    print('done.\n')

    results = sorted(results, key=lambda r: r[1])
    baseline = results[-1][1]

    for i, (name, sec_per_req) in enumerate(results):
        req_per_sec = 1 / sec_per_req
        ms_per_req = sec_per_req * 1000
        factor = int(baseline / sec_per_req)

        print('{3}. {0:.<15s}{1:.>06,.0f} req/sec or {2:0.3f} ms/req ({4}x)'.
              format(name, req_per_sec, ms_per_req, i + 1, factor))

    print('')
