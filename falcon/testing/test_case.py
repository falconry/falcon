# Copyright 2016 by Rackspace Hosting, Inc.
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

"""unittest-style base class and utilities for test cases.

This package includes a unittest-style base class and requests-like
utilities for simulating and validating HTTP requests.
"""

from __future__ import annotations

import importlib
import os
from types import ModuleType
from typing import Any
import unittest
import warnings

import falcon
import falcon.request

# TODO: Hoist for backwards compat. Remove in Falcon 5.0.
from falcon.testing.client import Result  # NOQA
from falcon.testing.client import TestClient
from falcon.util.deprecation import DeprecatedWarning

_TESTTOOLS_WARNING = (
    'falcon.testing.TestCase is rebased on testtools.TestCase. '
    'This integration is deprecated and will be removed in Falcon 5.0. '
    'Prefer unittest.TestCase (default) or pytest; see the testing tutorial. '
    'To keep using a custom TestCase base, set the FALCON_TESTING_TESTCASE_BASE '
    'environment variable to an import path (module:attribute or module.attribute).'
)


def _load_custom_testcase_base() -> type[unittest.TestCase] | None:
    """Load a custom TestCase base from FALCON_TESTING_TESTCASE_BASE, if set.

    The value may be ``module:attribute`` (preferred) or ``module.attribute``.
    """
    spec = os.environ.get('FALCON_TESTING_TESTCASE_BASE', '').strip()
    if not spec:
        return None

    if ':' in spec:
        module_name, _, attr_path = spec.partition(':')
    else:
        module_name, _, attr_path = spec.rpartition('.')
        if not module_name or not attr_path:
            raise ImportError(
                'FALCON_TESTING_TESTCASE_BASE must be module:attribute or '
                f'module.attribute, got {spec!r}'
            )

    module: ModuleType = importlib.import_module(module_name)
    obj: Any = module
    for part in attr_path.split('.'):
        obj = getattr(obj, part)

    if not isinstance(obj, type) or not issubclass(obj, unittest.TestCase):
        raise TypeError(
            'FALCON_TESTING_TESTCASE_BASE must resolve to a unittest.TestCase '
            f'subclass, got {obj!r}'
        )
    return obj


def _resolve_unittest_base() -> tuple[type[unittest.TestCase], bool]:
    """Return (base_class, used_testtools).

    Order:
    1. Custom base via FALCON_TESTING_TESTCASE_BASE
    2. testtools.TestCase if installed (deprecated path)
    3. unittest.TestCase
    """
    custom = _load_custom_testcase_base()
    if custom is not None:
        return custom, False

    try:
        import testtools as testtools_mod
    except ImportError:  # pragma: nocover
        return unittest.TestCase, False

    return testtools_mod.TestCase, True


_UnittestBase, _USED_TESTTOOLS = _resolve_unittest_base()
_testtools_deprecation_emitted = False


class TestCase(_UnittestBase, TestClient):  # type: ignore[misc, valid-type]
    """Extends :mod:`unittest` to support WSGI/ASGI functional testing.

    Note:
        If :mod:`testtools` is installed and no custom base is configured,
        :class:`falcon.testing.TestCase` is rebased on
        :class:`testtools.TestCase` for backwards compatibility. That path is
        **deprecated** and will be removed in Falcon 5.0. Prefer the standard
        library :mod:`unittest` (default when ``testtools`` is absent) or
        :mod:`pytest` (see the testing tutorial).

        To keep a custom base class (including ``testtools``), set the
        environment variable ``FALCON_TESTING_TESTCASE_BASE`` to an import path
        such as ``testtools:TestCase`` or ``mypkg.tests:MyBase``.

        .. versionchanged:: 4.4
            Automatic rebase onto :class:`testtools.TestCase` is deprecated
            and will be removed in Falcon 5.0. A
            :class:`~falcon.util.deprecation.DeprecatedWarning` is emitted when
            that path is used. Prefer :mod:`unittest` or :mod:`pytest`, or set
            ``FALCON_TESTING_TESTCASE_BASE`` for a custom base until 5.0.

    This base class provides some extra plumbing for unittest-style
    test cases, to help simulate WSGI or ASGI requests without having
    to spin up an actual web server. Various simulation methods are
    derived from :class:`falcon.testing.TestClient`.

    Simply inherit from this class in your test case classes instead of
    :class:`unittest.TestCase`.
    """

    # NOTE(vytas): Here we have to restore __test__ to allow collecting tests!
    __test__ = True

    # NOTE(vytas): Parametrize with [Any, Any] because the app under test may
    #   use custom Request/Response subclasses.
    # TODO(vytas): A future change could make TestCase generic over the app's
    #   request/response types (leveraging TypeVar defaults on Python 3.13+).
    app: falcon.App[Any, Any]
    """A WSGI or ASGI application to target when simulating
    requests (defaults to ``falcon.App()``). When testing your
    application, you will need to set this to your own instance
    of :class:`falcon.App` or :class:`falcon.asgi.App`. For
    example::

        from falcon import testing
        import myapp


        class MyTestCase(testing.TestCase):
            def setUp(self):
                super(MyTestCase, self).setUp()

                # Assume the hypothetical `myapp` package has a
                # function called `create()` to initialize and
                # return a `falcon.App` instance.
                self.app = myapp.create()


        class TestMyApp(MyTestCase):
            def test_get_message(self):
                doc = {'message': 'Hello world!'}

                result = self.simulate_get('/messages/42')
                self.assertEqual(result.json, doc)
    """

    def setUp(self) -> None:
        global _testtools_deprecation_emitted
        if _USED_TESTTOOLS and not _testtools_deprecation_emitted:
            warnings.warn(
                _TESTTOOLS_WARNING,
                category=DeprecatedWarning,
                stacklevel=2,
            )
            _testtools_deprecation_emitted = True

        super().setUp()

        app = falcon.App()

        # NOTE(kgriffs): Don't use super() to avoid triggering
        # unittest.TestCase.__init__()
        TestClient.__init__(self, app)
