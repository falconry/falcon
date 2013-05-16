#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
from collections import defaultdict
import cProfile
from decimal import Decimal
import gc
import random
import sys
import timeit

import falcon.testing as helpers

from falcon.bench import create  # NOQA


def bench(name, iterations, env):
    func = create_bench(name, env)

    gc.collect()
    total_sec = timeit.timeit(func, setup=gc.enable, number=iterations)

    sec_per_req = Decimal(total_sec) / Decimal(iterations)

    sys.stdout.write('.')
    sys.stdout.flush()

    return (name, sec_per_req)


def profile(name, env, output=None):
    if output:
        filename = name + '-' + output
        print('Profiling %s ==> %s' %(name, filename))

    else:
        filename = None

        title = name + ' profile'
        print()
        print('=' * len(title))
        print(title)
        print('=' * len(title))

    func = create_bench(name, env)

    gc.collect()
    code = 'for x in xrange(10000): func()'
    cProfile.runctx(code, locals(), globals(),
                    sort='tottime', filename=filename)


def create_bench(name, env):
    srmock = helpers.StartResponseMock()

    # env = helpers.create_environ('/hello', query_string='limit=10',
    #                              headers=request_headers)

    body = helpers.rand_string(0, 10240)  # NOQA
    headers = {'X-Test': 'Funky Chicken'}  # NOQA

    function = name.lower().replace('-', '_')
    app = eval('create.{0}(body, headers)'.format(function))

    def bench():
        app(env, srmock)
        if srmock.status != '200 OK':
            raise AssertionError(srmock.status + ' != 200 OK')

    return bench


def consolidate_datasets(datasets):
    results = defaultdict(list)
    for dataset in datasets:
        for name, sec_per_req in dataset:
            results[name].append(sec_per_req)

    return [(name, min(vector)) for name, vector in results.items()]


def round_to_int(dec):
    return int(dec.to_integral_value())


def avg(array):
    return sum(array) / len(array)


def hello_env():
    request_headers = {'Content-Type': 'application/json'}
    return helpers.create_environ('/hello/584/test',
                                  query_string='limit=10',
                                  headers=request_headers)


def queues_env():
    request_headers = {'Content-Type': 'application/json'}
    path = ('/v1/852809/queues/0fd4c8c6-bd72-11e2-8e47-db5ebd4c8125'
            '/claims/db5ebd4c8125')

    return helpers.create_environ(path, query_string='limit=10',
                                  headers=request_headers)


def get_env(framework):
    return queues_env() if framework == 'falcon-ext' else hello_env()


def run(frameworks, repetitions, iterations):
    # Skip any frameworks that are not installed
    for name in frameworks:
        try:
            create_bench(name, hello_env())
        except ImportError:
            print('Skipping missing library: ' + name)
            del frameworks[frameworks.index(name)]

    print()

    if not frameworks:
        print('Nothing to do.\n')
        return

    datasets = []
    for r in range(repetitions):
        random.shuffle(frameworks)

        sys.stdout.write('Benchmarking, Round %d of %d' %
                         (r + 1, repetitions))
        sys.stdout.flush()

        dataset = [bench(framework, iterations, get_env(framework))
                   for framework in frameworks]

        datasets.append(dataset)
        print('done.')

    return datasets


def main():
    frameworks = [
        'bottle',
        'falcon',
        'falcon-ext',
        'flask',
        'pecan',
        'werkzeug'
    ]

    parser = argparse.ArgumentParser(description="Falcon benchmark runner")
    parser.add_argument('-b', '--benchmark', type=str, action='append',
                        choices=frameworks, dest='frameworks')
    parser.add_argument('-i', '--iterations', type=int, default=50000)
    parser.add_argument('-r', '--repetitions', type=int, default=3)
    parser.add_argument('-p', '--profile', action='store_true')
    parser.add_argument('-o', '--profile-output', type=str, default=None)
    args = parser.parse_args()

    if args.frameworks:
        frameworks = args.frameworks

    if args.profile:
        for name in frameworks:
            profile(name, get_env(name), args.profile_output)

    else:
        datasets = run(frameworks, args.repetitions, args.iterations)

        dataset = consolidate_datasets(datasets)
        dataset = sorted(dataset, key=lambda r: r[1])
        baseline = dataset[-1][1]

        print('\nResults:\n')

        for i, (name, sec_per_req) in enumerate(dataset):
            req_per_sec = round_to_int(Decimal(1) / sec_per_req)
            us_per_req = (sec_per_req * Decimal(10 ** 6))
            factor = round_to_int(baseline / sec_per_req)

            print('{3}. {0:.<15s}{1:.>06,d} req/sec or {2: >3.2f} μs/req ({4}x)'.
                  format(name, req_per_sec, us_per_req, i + 1, factor))

    print()
