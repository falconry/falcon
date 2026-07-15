"""Tests for falcon.testing.TestCase base resolution and testtools deprecation."""

from __future__ import annotations

import importlib
import sys
import unittest
import warnings

import pytest

from falcon.util.deprecation import DeprecatedWarning


def _fresh_test_case_module(monkeypatch, *, env: str | None = None, block_testtools: bool = False):
    """Import a clean falcon.testing.test_case under controlled env/import conditions."""
    if env is None:
        monkeypatch.delenv('FALCON_TESTING_TESTCASE_BASE', raising=False)
    else:
        monkeypatch.setenv('FALCON_TESTING_TESTCASE_BASE', env)

    if block_testtools:
        real_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'testtools' or (isinstance(name, str) and name.startswith('testtools.')):
                raise ImportError('testtools blocked for unit test')
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr('builtins.__import__', fake_import)
        # Prevent a previously imported testtools module from satisfying imports.
        monkeypatch.setitem(sys.modules, 'testtools', None)

    # Drop modules that capture base class at import time.
    for name in list(sys.modules):
        if name == 'falcon.testing.test_case' or name == 'falcon.testing':
            sys.modules.pop(name, None)

    import falcon.testing.test_case as tc

    return tc


def test_resolve_helpers_default_unittest_when_testtools_missing(monkeypatch):
    tc = _fresh_test_case_module(monkeypatch, block_testtools=True)

    base, used = tc._resolve_unittest_base()
    assert used is False
    assert base is unittest.TestCase
    assert tc._USED_TESTTOOLS is False
    assert issubclass(tc.TestCase, unittest.TestCase)


def test_resolve_helpers_testtools_when_installed(monkeypatch):
    pytest.importorskip('testtools')
    import testtools

    tc = _fresh_test_case_module(monkeypatch)

    assert tc._USED_TESTTOOLS is True
    assert tc._UnittestBase is testtools.TestCase
    assert issubclass(tc.TestCase, testtools.TestCase)


def test_testtools_path_emits_deprecation_once(monkeypatch):
    pytest.importorskip('testtools')
    tc = _fresh_test_case_module(monkeypatch)
    assert tc._USED_TESTTOOLS is True

    class Sample(tc.TestCase):
        def test_ok(self):
            self.assertTrue(True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        Sample('test_ok').setUp()
        Sample('test_ok').setUp()

    dep = [w for w in caught if isinstance(w.message, DeprecatedWarning)]
    assert len(dep) == 1
    text = str(dep[0].message)
    assert 'deprecated' in text.lower()
    assert 'FALCON_TESTING_TESTCASE_BASE' in text
    assert '5.0' in text


def test_custom_base_via_env_uses_unittest_without_deprecation(monkeypatch):
    pytest.importorskip('testtools')
    tc = _fresh_test_case_module(monkeypatch, env='unittest:TestCase')

    assert tc._USED_TESTTOOLS is False
    assert tc._UnittestBase is unittest.TestCase

    class Sample(tc.TestCase):
        def test_ok(self):
            self.assertTrue(True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        Sample('test_ok').setUp()

    assert not any(isinstance(w.message, DeprecatedWarning) for w in caught)


def test_custom_base_dotted_form(monkeypatch):
    tc = _fresh_test_case_module(monkeypatch, env='unittest.TestCase', block_testtools=True)
    assert tc._UnittestBase is unittest.TestCase
    assert tc._USED_TESTTOOLS is False


def test_custom_base_explicit_testtools_is_escape_hatch(monkeypatch):
    """Explicit env opt-in keeps testtools without the auto-rebase deprecation flag."""
    pytest.importorskip('testtools')
    import testtools

    tc = _fresh_test_case_module(monkeypatch, env='testtools:TestCase')

    assert tc._USED_TESTTOOLS is False
    assert tc._UnittestBase is testtools.TestCase

    class Sample(tc.TestCase):
        def test_ok(self):
            self.assertTrue(True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        Sample('test_ok').setUp()

    assert not any(isinstance(w.message, DeprecatedWarning) for w in caught)


def test_invalid_custom_base_env_raises(monkeypatch):
    monkeypatch.setenv('FALCON_TESTING_TESTCASE_BASE', 'not_a_valid_spec')
    for name in ('falcon.testing.test_case', 'falcon.testing'):
        sys.modules.pop(name, None)

    with pytest.raises((ImportError, ModuleNotFoundError, AttributeError, TypeError)):
        importlib.import_module('falcon.testing.test_case')


def test_custom_base_must_be_testcase_subclass(monkeypatch):
    monkeypatch.setenv('FALCON_TESTING_TESTCASE_BASE', 'typing:Any')
    for name in ('falcon.testing.test_case', 'falcon.testing'):
        sys.modules.pop(name, None)

    with pytest.raises(TypeError, match='unittest.TestCase'):
        importlib.import_module('falcon.testing.test_case')
