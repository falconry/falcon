#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
from collections import defaultdict
from decimal import Decimal
import gc
import random
import sys
import timeit

import falcon.testing as helpers

from falcon.bench import create  # NOQA


def avg(array):
    return sum(array) / len(array)


def bench(name, iterations):
    func = create_bench(name)

    gc.collect()
    total_sec = timeit.timeit(func, setup=gc.enable, number=iterations)

    sec_per_req = Decimal(total_sec) / Decimal(iterations)

    sys.stdout.write('.')
    sys.stdout.flush()

    return (name, sec_per_req)


def create_bench(name):
    srmock = helpers.StartResponseMock()

    request_headers = {'Content-Type': 'application/json'}
    env = helpers.create_environ('/hello/584/test', query_string='limit=10',
                                 headers=request_headers)

    # env = helpers.create_environ('/hello', query_string='limit=10',
    #                              headers=request_headers)

    body = helpers.rand_string(0, 10240)  # NOQA
    headers = {'X-Test': 'Funky Chicken'}  # NOQA

    app = eval('create.{0}(body, headers)'.format(name.lower()))

    def bench():
        app(env, srmock)

    return bench


def consolidate_datasets(datasets):
    results = defaultdict(list)
    for dataset in datasets:
        for name, sec_per_req in dataset:
            results[name].append(sec_per_req)

    return [(name, min(vector)) for name, vector in results.items()]


def round_to_int(dec):
    return int(dec.to_integral_value())


def run():
    frameworks = [
        'flask', 'werkzeug', 'falcon',
        'pecan', 'bottle', 'cherrypy'
    ]

    parser = argparse.ArgumentParser(description="Falcon benchmark runner")
    parser.add_argument('-b', '--benchmark', type=str, action='append',
                        choices=frameworks, dest='frameworks')
    parser.add_argument('-i', '--iterations', type=int, default=50000)
    parser.add_argument('-r', '--repetitions', type=int, default=3)
    args = parser.parse_args()

    if args.frameworks:
        frameworks = args.frameworks

    # Skip any frameworks that are not installed
    for name in frameworks:
        try:
            create_bench(name)
        except ImportError:
            print('Skipping missing library: ' + name)
            del frameworks[frameworks.index(name)]

    print('')

    if not frameworks:
        print('Nothing to do.\n')
        return

    datasets = []
    for r in range(args.repetitions):
        random.shuffle(frameworks)

        sys.stdout.write('Benchmarking, Round %d of %d' %
                         (r + 1, args.repetitions))
        sys.stdout.flush()
        dataset = [bench(framework, args.iterations)
                   for framework in frameworks]

        datasets.append(dataset)
        print('done.')

    dataset = consolidate_datasets(datasets)
    dataset = sorted(dataset, key=lambda r: r[1])
    baseline = dataset[-1][1]

    print('\nResults:\n')

    for i, (name, sec_per_req) in enumerate(dataset):
        req_per_sec = round_to_int(Decimal(1) / sec_per_req)
        us_per_req = round_to_int(sec_per_req * Decimal(10 ** 6))
        factor = round_to_int(baseline / sec_per_req)

        print('{3}. {0:.<15s}{1:.>06,d} req/sec or {2: >03d} μs/req ({4}x)'.
              format(name, req_per_sec, us_per_req, i + 1, factor))

    print('')
