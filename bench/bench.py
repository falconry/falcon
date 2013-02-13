#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import random
import argparse
import timeit

from create import *

sys.path.append('..')
import falcon.testing as helpers
del sys.path[-1]


def avg(array):
    return sum(array) / len(array)


def bench(name, iterations=10000, repeat=5):
    func = create_bench(name)
    results = timeit.repeat(func, number=iterations, repeat=repeat)

    sec_per_req = avg(results) / iterations

    sys.stdout.write('.')
    sys.stdout.flush()

    return (name, sec_per_req)


def create_bench(name):
    srmock = helpers.StartResponseMock()
    env = helpers.create_environ('/hello/584/test', query_string='limit=10')
    body = helpers.rand_string(0, 10240)  # NOQA
    headers = {'X-Test': 'Funky Chicken'}  # NOQA

    app = eval('create_{0}(body, headers)'.format(name.lower()))

    def bench():
        app(env, srmock)

    return bench


if __name__ == '__main__':
    frameworks = [
        'Wheezy', 'Flask', 'Werkzeug', 'Falcon', 'Pecan', 'Bottle', 'CherryPy'
    ]

    parser = argparse.ArgumentParser(description="Falcon benchmark runner")
    parser.add_argument('-b', '--benchmark', type=str, action='append',
                        choices=frameworks, dest='frameworks')
    parser.add_argument('-i', '--iterations', type=int, default=100000)
    parser.add_argument('-r', '--repetitions', type=int, default=10)
    args = parser.parse_args()

    if args.frameworks:
        frameworks = args.frameworks
    else:
        # wheezy.http isn't really a framework - doesn't even have a router
        del frameworks[frameworks.index('Wheezy')]

    random.shuffle(frameworks)

    sys.stdout.write('\nBenchmarking')
    sys.stdout.flush()
    results = [bench(framework, args.iterations, args.repetitions)
               for framework in frameworks]
    print('done.\n')

    results = sorted(results, key=lambda r: r[1])
    baseline = results[-1][1]

    for i, (name, sec_per_req) in enumerate(results):
        req_per_sec = 1 / sec_per_req
        ms_per_req = sec_per_req * 1000
        factor = int(baseline / sec_per_req + 0.1)

        print('{3}. {0:.<15s}{1:.>06,.0f} req/sec or {2:0.1f} μs/req ({4}x)'.
              format(name, req_per_sec, ms_per_req * 1000, i + 1, factor))

    print('')
