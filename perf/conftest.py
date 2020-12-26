# Copyright 2020 by Vytautas Liuolia.
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

import math
import pathlib
import platform
import subprocess
import sys

import numpy
import pytest
import yaml

HERE = pathlib.Path(__file__).resolve().parent


def _platform():
    # TODO(vytas): Add support for Cython, PyPy etc.
    label = platform.python_implementation().lower()
    version = ''.join(platform.python_version_tuple()[:2])
    return f'{label}_{version}'


class Gauge:
    GAUGE_ENV = {
        'LC_ALL': 'en_US.UTF-8',
        'LANG': 'en_US.UTF-8',
        'PYTHONHASHSEED': '0',
        'PYTHONIOENCODING': 'utf-8',
    }

    def __init__(self, metric):
        with open(HERE / 'BASELINE.yaml', encoding='utf-8') as baseline:
            config = yaml.safe_load(baseline)

        platform_label = _platform()
        platform_spec = config.get(platform_label)
        assert platform_spec, (
            f'no performance baseline established for {platform_label} yet',
        )

        self._metric = metric
        self._spec = platform_spec[metric]

    def _fit_data(self, iterations, times):
        # NOTE(vytas): Least-squares fitting solution straight from
        #   https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html
        x = numpy.array(iterations, dtype=float)
        y = numpy.array(times, dtype=float)
        A = numpy.vstack([x, numpy.ones(len(x))]).T
        (cost, _), residuals, _, _ = numpy.linalg.lstsq(A, y, rcond=None)

        N = len(times)
        rmsd = math.sqrt(residuals / (N - 2))
        cv_rmsd = rmsd / numpy.mean(y)
        return (cost, cv_rmsd)

    def _measure_data_point(self, number):
        command = (
            sys.executable,
            'cachegrind.py',
            sys.executable,
            '-m',
            f'metrics.{self._metric}',
            str(number),
        )
        print('\n\nrunning cachegrind:', ' '.join(command), '\n')
        output = subprocess.check_output(command, cwd=HERE, env=self.GAUGE_ENV)
        output = output.decode().strip()
        print(f'\n{output}')

        return int(output.strip())

    def measure(self):
        iterations = self._spec['points']

        times = []
        for number in iterations:
            times.append(self._measure_data_point(number))

        cost, cv_rmsd = self._fit_data(iterations, times)
        print('\nestimated cost per iteration:', cost)
        print('estimated CV of RMSD:', cv_rmsd)

        expected_cost = self._spec['expected']['cost']
        expected_variation = self._spec['expected']['variation']
        tolerance = self._spec['tolerance']

        assert cost > expected_cost / 10, (
            'estimated cost per iteration is very low; is the metric broken?')
        assert cv_rmsd < expected_variation, (
            'cachegrind results vary too much between iterations')

        assert cost > expected_cost * (1 + min(tolerance)), (
            'too good! please revise the baseline if you optimized the code')
        assert cost < expected_cost * (1 + max(tolerance)), (
            'performance regression measured!')


def pytest_configure(config):
    config.addinivalue_line('markers', 'asgi: "asgi" performance metric')
    config.addinivalue_line('markers', 'hello: "hello" performance metric')
    config.addinivalue_line('markers', 'media: "media" performance metric')
    config.addinivalue_line('markers', 'query: "query" performance metric')


@pytest.fixture()
def gauge():
    def _method(metric):
        Gauge(metric).measure()

    return _method
