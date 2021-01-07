#!/usr/bin/env python

# Copyright 2014 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
from collections import defaultdict, deque
from decimal import Decimal
import gc
import inspect
import platform
import random
import sys
import tempfile
import timeit

try:
    import cProfile
except ImportError:
    import profile as cProfile

try:
    import guppy
except ImportError:
    heapy = None
else:
    heapy = guppy.hpy()

try:
    import pprofile
except ImportError:
    pprofile = None

try:
    import vmprof
    from vmshare.service import Service
except ImportError:
    vmprof = None

from falcon.bench import create  # NOQA
from falcon.constants import PYPY
import falcon.testing as helpers


# NOTE(kgriffs): Based on testing, these values provide a ceiling that's
# several times higher than fast x86 hardware can achieve today.
ITER_DETECTION_MAX_ATTEMPTS = 27
ITER_DETECTION_MULTIPLIER = 1.7
ITER_DETECTION_STARTING = 3000

# NOTE(kgriffs): Benchmark duration range, in seconds, to target
ITER_DETECTION_DURATION_MIN = 1.0
ITER_DETECTION_DURATION_MAX = 6.0

JIT_WARMING_MULTIPLIER = 30

BODY = helpers.rand_string(10240, 10240).encode('utf-8') # NOQA
HEADERS = {'X-Test': 'Funky Chicken'}  # NOQA


class StartResponseMockLite:
    """Mock object representing a WSGI `start_response` callable."""

    def __init__(self):
        self._called = 0
        self.status = None
        self.headers = None
        self.exc_info = None

    def __call__(self, status, headers, exc_info=None):
        """Implement the PEP-3333 `start_response` protocol."""

        self._called += 1

        self.status = status
        self.headers = headers
        self.exc_info = exc_info

    @property
    def call_count(self):
        return self._called


def bench(func, iterations, stat_memory):
    gc.collect()
    heap_diff = None

    if heapy and stat_memory:
        heap_before = heapy.heap()

    total_sec = timeit.timeit(func, setup=gc.enable, number=iterations)

    if heapy and stat_memory:
        heap_diff = heapy.heap() - heap_before

    sec_per_req = Decimal(str(total_sec)) / Decimal(str(iterations))

    return (sec_per_req, heap_diff)


def determine_iterations(func):
    # NOTE(kgriffs): Algorithm adapted from IPython's magic timeit
    # function to determine iterations so that 0.2 <= total time < 2.0
    iterations = ITER_DETECTION_STARTING
    for __ in range(1, ITER_DETECTION_MAX_ATTEMPTS):
        gc.collect()

        total_sec = timeit.timeit(
            func,
            setup=gc.enable,
            number=int(iterations)
        )

        if total_sec >= ITER_DETECTION_DURATION_MIN:
            assert total_sec < ITER_DETECTION_DURATION_MAX
            break

        iterations *= ITER_DETECTION_MULTIPLIER

    return int(iterations)


def profile(name, env, filename=None, verbose=False):
    if filename:
        filename = name + '-' + filename
        print('Profiling %s ==> %s' % (name, filename))

    else:
        filename = None

        title = name + ' profile'
        print()
        print('=' * len(title))
        print(title)
        print('=' * len(title))

    func = create_bench(name, env)
    gc.collect()

    num_iterations = 100000

    if PYPY:
        print('JIT warmup...')

        # TODO(kgriffs): Measure initial time, and keep iterating until
        # performance increases and then steadies
        for x in range(num_iterations * JIT_WARMING_MULTIPLIER):
            func()

        print('Ready.')

    code = 'for x in range({0}): func()'.format(num_iterations)

    if verbose:
        if pprofile is None:
            print('pprofile not found. Please install pprofile and try again.')
            return

        pprofile.runctx(code, locals(), globals(), filename=filename)

    else:
        cProfile.runctx(code, locals(), globals(),
                        sort='tottime', filename=filename)


def profile_vmprof(name, env):
    if vmprof is None:
        print('vmprof not found. Please install vmprof and try again.')
        return

    func = create_bench(name, env)
    gc.collect()

    #
    # Based on: https://github.com/vmprof/vmprof-python/blob/master/vmprof/__main__.py
    #

    prof_file = tempfile.NamedTemporaryFile(delete=False)
    filename = prof_file.name

    vmprof.enable(prof_file.fileno())

    try:
        for __ in range(1000000):
            func()

    except BaseException as e:
        if not isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise

    vmprof.disable()

    service = Service('vmprof.com')
    service.post({
        Service.FILE_CPU_PROFILE: filename,
        Service.FILE_JIT_PROFILE: filename + '.jit',
        'argv': ' '.join(sys.argv[:]),
        'VM': platform.python_implementation(),
    })

    prof_file.close()


def exhaust(iterator_or_generator):
    # from https://docs.python.org/dev/library/itertools.html#itertools-recipes
    deque(iterator_or_generator, maxlen=0)


def create_bench(name, env):
    srmock = StartResponseMockLite()

    function = name.lower().replace('-', '_')
    app = eval('create.{0}(BODY, HEADERS)'.format(function))

    def bench():
        app(env, srmock)
        assert srmock.status == '200 OK'

    def bench_generator():
        exhaust(app(env, srmock))
        assert srmock.status == '200 OK'

    if inspect.isgeneratorfunction(app):
        return bench_generator
    else:
        return bench


def consolidate_datasets(datasets):
    results = defaultdict(list)
    for dataset in datasets:
        for name, sec_per_req, _ in dataset:
            results[name].append(sec_per_req)

    return [(name, min(vector)) for name, vector in results.items()]


def round_to_int(dec):
    return int(dec.to_integral_value())


def avg(array):
    return sum(array) / len(array)


def hello_env():
    request_headers = {'Content-Type': 'application/json'}
    return helpers.create_environ('/hello/584/test',
                                  query_string='limit=10&thing=ab',
                                  headers=request_headers)


def queues_env():
    request_headers = {'Content-Type': 'application/json'}
    path = ('/v1/852809/queues/0fd4c8c6-bd72-11e2-8e47-db5ebd4c8125'
            '/claims/db5ebd4c8125')

    qs = 'limit=10&thing=a+b&x=%23%24'
    return helpers.create_environ(path, query_string=qs,
                                  headers=request_headers)


def get_env(framework):
    return queues_env() if framework == 'falcon-ext' else hello_env()


def run(frameworks, trials, iterations, stat_memory):
    # Skip any frameworks that are not installed
    for name in frameworks:
        try:
            create_bench(name, hello_env())
        except ImportError as ex:
            print(ex)
            print('Skipping missing library: ' + name)
            del frameworks[frameworks.index(name)]

    print()

    datasets = []

    if not frameworks:
        print('Nothing to do.\n')
        return datasets

    benchmarks = []
    for name in frameworks:
        bm = create_bench(name, get_env(name))

        bm_iterations = iterations if iterations else determine_iterations(bm)

        if PYPY:
            print('{}: JIT warmup'.format(name))

            # TODO(kgriffs): Measure initial time, and keep iterating until
            # performance increases and then steadies
            bench(bm, bm_iterations * JIT_WARMING_MULTIPLIER, False)

        bm_iterations = iterations if iterations else determine_iterations(bm)

        benchmarks.append((name, bm_iterations, bm))
        print('{}: {} iterations'.format(name, bm_iterations))

    print()

    for r in range(trials):
        random.shuffle(frameworks)

        sys.stdout.write('Benchmarking, Trial %d of %d' %
                         (r + 1, trials))
        sys.stdout.flush()

        dataset = []
        for name, bm_iterations, bm in benchmarks:
            sec_per_req, heap_diff = bench(
                bm,
                bm_iterations,
                stat_memory
            )

            dataset.append((name, sec_per_req, heap_diff))

            sys.stdout.write('.')
            sys.stdout.flush()

        datasets.append(dataset)
        print('done.')

    return datasets


def main():
    frameworks = [
        'bottle',
        'django',
        'falcon',
        'falcon-ext',
        'flask',
        'pecan',
        'werkzeug',
    ]

    parser = argparse.ArgumentParser(description='Falcon benchmark runner')
    parser.add_argument('-b', '--benchmark', type=str, action='append',
                        choices=frameworks, dest='frameworks', nargs='+')
    parser.add_argument('-i', '--iterations', type=int, default=0)
    parser.add_argument('-t', '--trials', type=int, default=10)
    parser.add_argument('-p', '--profile', type=str,
                        choices=['standard', 'verbose', 'vmprof'])
    parser.add_argument('-o', '--profile-output', type=str, default=None)
    parser.add_argument('-m', '--stat-memory', action='store_true')
    args = parser.parse_args()

    if args.stat_memory and heapy is None:
        print('WARNING: Guppy not installed; memory stats are unavailable.\n')

    if args.frameworks:
        frameworks = args.frameworks

    # Normalize frameworks type
    normalized_frameworks = []
    for one_or_many in frameworks:
        if isinstance(one_or_many, list):
            normalized_frameworks.extend(one_or_many)
        else:
            normalized_frameworks.append(one_or_many)

    frameworks = normalized_frameworks

    # Profile?
    if args.profile:
        framework = 'falcon-ext'

        if args.profile == 'vmprof':
            profile_vmprof(framework, get_env(framework))
        else:
            profile(framework, get_env(framework),
                    filename=args.profile_output,
                    verbose=(args.profile == 'verbose'))

        print()
        return

    # Otherwise, benchmark
    datasets = run(frameworks, args.trials, args.iterations,
                   args.stat_memory)

    if not datasets:
        return

    dataset = consolidate_datasets(datasets)
    dataset = sorted(dataset, key=lambda r: r[1])
    baseline = dataset[-1][1]

    print('\nResults:\n')

    for i, (name, sec_per_req) in enumerate(dataset):
        req_per_sec = round_to_int(Decimal(1) / sec_per_req)
        us_per_req = (sec_per_req * Decimal(10 ** 6))
        factor = round_to_int(baseline / sec_per_req)

        print('{3}. {0:.<20s}{1:.>06d} req/sec or {2: >3.2f} μs/req ({4}x)'.
              format(name, req_per_sec, us_per_req, i + 1, factor))

    if heapy and args.stat_memory:
        print()

        for name, _, heap_diff in datasets[0]:
            title = 'Memory change induced by ' + name
            print()
            print('=' * len(title))
            print(title)
            print('=' * len(title))
            print(heap_diff)

    print()


if __name__ == '__main__':
    main()
