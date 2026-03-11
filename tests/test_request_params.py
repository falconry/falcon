from __future__ import annotations

from typing import Any

import pytest

from falcon import errors
from falcon.request import Request


class DummyRequestParams:
    def __init__(self, params: dict[str, Any]):
        self._params = params

    def get_param_as_list(self, name: str):
        if name == 'bad':
            raise errors.HTTPBadRequest()
        return self._params.get(name)

    def get_param_as_dict(
        self,
        name: str,
        required: bool = False,
        deep_object: bool = False,
        store: dict[str, Any] | None = None,
        default: Any | None = None,
    ) -> Any: ...


# NOTE(StepanUFL): If a better way to make this play well with mypy exists...
DummyRequestParams.get_param_as_dict = Request.get_param_as_dict  # type: ignore[method-assign, assignment]


@pytest.mark.parametrize(
    'params,expected',
    [
        ({'user[name]': 'Ash', 'user[age]': '36'}, {'name': 'Ash', 'age': '36'}),
        ({'user[empty]': ''}, {'empty': ''}),
    ],
)
def test_deep_object_success(params, expected):
    req = DummyRequestParams(params)
    result = req.get_param_as_dict('user', deep_object=True)
    assert result == expected


def test_deep_object_missing_required():
    req = DummyRequestParams({})
    with pytest.raises(errors.HTTPMissingParam):
        req.get_param_as_dict('user', deep_object=True, required=True)


def test_deep_object_default_used_when_missing():
    req = DummyRequestParams({})
    default = {'fallback': 123}
    result = req.get_param_as_dict('user', deep_object=True, default=default)
    assert result == default


def test_regular_param_success_even_length():
    req = DummyRequestParams({'pair': ['a', '1', 'b', '2']})
    result = req.get_param_as_dict('pair')
    assert result == {'a': '1', 'b': '2'}


def test_regular_param_missing_required():
    req = DummyRequestParams({})
    with pytest.raises(errors.HTTPMissingParam):
        req.get_param_as_dict('pair', required=True)


def test_regular_param_odd_length_raises_invalid():
    req = DummyRequestParams({'pair': ['a', 'b', 'c']})
    with pytest.raises(errors.HTTPInvalidParam):
        req.get_param_as_dict('pair')


def test_regular_param_default_used_when_missing():
    req = DummyRequestParams({})
    result = req.get_param_as_dict('pair', default={'x': 'y'})
    assert result == {'x': 'y'}


def test_regular_param_bad_request_raises_invalid():
    req = DummyRequestParams({'ok': ['1', '2']})
    with pytest.raises(errors.HTTPInvalidParam):
        req.get_param_as_dict('bad')


def test_store_argument_is_updated():
    req = DummyRequestParams({'pair': ['a', '1', 'b', '2']})
    store = {}
    result = req.get_param_as_dict('pair', store=store)
    assert result == {'a': '1', 'b': '2'}
    assert store == {'a': '1', 'b': '2'}


def test_deep_object_with_list_values():
    req = DummyRequestParams({'user[name]': ['Bond'], 'user[id]': ['007']})
    result = req.get_param_as_dict('user', deep_object=True)
    assert result == {'name': 'Bond', 'id': '007'}


@pytest.mark.skip(reason='Delimiter functionality not implemented')
def test_regular_param_with_delimiter_argument_is_ignored_but_accepted():
    req = DummyRequestParams({'pair': ['a', '1', 'b', '2']})
    result = req.get_param_as_dict('pair')
    assert result == {'a': '1', 'b': '2'}


def test_deep_object_skips_non_matching_bracketed_keys():
    params = {
        'user[name]': 'Ash',
        'weird]': 'looking',
    }
    req = DummyRequestParams(params)
    result = req.get_param_as_dict('user', deep_object=True)
    assert result == {'name': 'Ash'}
