from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

import falcon


class Validator:
    """Base validator class."""

    exceptions: Union[Tuple[Type[Exception], ...], Type[Exception]]
    """The exceptions raised by the validation library"""

    @classmethod
    @abstractmethod
    def from_schema(cls, schema: Any) -> Validator:
        """Construct the class from a schema object."""

    @abstractmethod
    def validate(self, media: Any) -> None:
        """Validates the input media."""

    @abstractmethod
    def get_exception_message(self, exception: Exception) -> Optional[str]:
        """Returns a message from an exception."""


_T = TypeVar('_T')


def validator_factory(
    validator: Type[Validator], req_schema: Any, resp_schema: Any, is_async: bool
) -> Callable[[_T], _T]:
    """Creates a validator decorator for that uses the specified ``Validator`` class.

    Args:
        validator (Type[Validator]): The validator class.
        req_schema (Any): The schema used in the request body. Type will depend on
            what is accepted by ``Validator.from_schema``.
            When ``None`` validation will be skipped.
        resp_schema (Any): The schema used in the response body. Type will depend
            on what is accepted by ``Validator.from_schema``.
            When ``None`` validation will be skipped.
        is_async (bool): Set to ``True`` to force use of the async validator.
    """

    def decorator(func: _T) -> _T:
        if iscoroutinefunction(func) or is_async:
            return _validate_async(validator, func, req_schema, resp_schema)

        return _validate(validator, func, req_schema, resp_schema)

    return decorator


def _validate(
    validator: Type[Validator], func, req_schema: Any, resp_schema: Any
) -> Any:
    req_validator = None if req_schema is None else validator.from_schema(req_schema)
    resp_validator = None if resp_schema is None else validator.from_schema(resp_schema)

    @wraps(func)
    def wrapper(self, req, resp, *args, **kwargs):
        if req_validator is not None:
            try:
                req_validator.validate(req.media)
            except req_validator.exceptions as ex:
                raise falcon.MediaValidationError(
                    title='Request data failed validation',
                    description=req_validator.get_exception_message(ex),
                ) from ex

        result = func(self, req, resp, *args, **kwargs)

        if resp_validator is not None:
            try:
                resp_validator.validate(resp.media)
            except resp_validator.exceptions as ex:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                ) from ex

        return result

    return wrapper


def _validate_async(
    validator: Type[Validator], func, req_schema: Any, resp_schema: Any
) -> Any:
    req_validator = None if req_schema is None else validator.from_schema(req_schema)
    resp_validator = None if resp_schema is None else validator.from_schema(resp_schema)

    @wraps(func)
    async def wrapper(self, req, resp, *args, **kwargs):
        if req_validator is not None:
            m = await req.get_media()

            try:
                req_validator.validate(m)
            except req_validator.exceptions as ex:
                raise falcon.MediaValidationError(
                    title='Request data failed validation',
                    description=req_validator.get_exception_message(ex),
                ) from ex

        result = await func(self, req, resp, *args, **kwargs)

        if resp_validator is not None:
            try:
                resp_validator.validate(resp.media)
            except resp_validator.exceptions as ex:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                ) from ex

        return result

    return wrapper
