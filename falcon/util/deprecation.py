# Copyright 2013 by Rackspace Hosting, Inc.
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

"""Miscellaneous deprecation utilities.

This module provides decorators to mark functions and classes as deprecated.
"""

import functools
import warnings


__all__ = (
    'DeprecatedWarning',
    'deprecated',
    'deprecated_args',
)


# NOTE(kgriffs): We don't want our deprecations to be ignored by default,
# so create our own type.
#
# TODO(kgriffs): Revisit this decision if users complain.
class DeprecatedWarning(UserWarning):
    pass


def deprecated(instructions, is_property=False, method_name=None):
    """Flag a method as deprecated.

    This function returns a decorator which can be used to mark deprecated
    functions. Applying this decorator will result in a warning being
    emitted when the function is used.

    Args:
        instructions (str): Specific guidance for the developer, e.g.:
            'Please migrate to add_proxy(...)'.
        is_property (bool): If the deprecated object is a property. It
            will omit the ``(...)`` from the generated documentation.
        method_name (str, optional): Set to override the name of the
            deprecated function or property in the generated
            documentation (default ``None``). This is useful when
            decorating an alias that carries the target's ``__name__``.

    """

    def decorator(func):

        object_name = 'property' if is_property else 'function'
        post_name = '' if is_property else '(...)'
        message = 'Call to deprecated {} {}{}. {}'.format(
            object_name, method_name or func.__name__, post_name, instructions
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(message, category=DeprecatedWarning, stacklevel=2)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def deprecated_args(*, allowed_positional, is_method=True):
    """Flag a method call with positional args as deprecated.

    Keyword Args:
        allowed_positional (int): Number of allowed positional arguments
        is_method (bool, optional): The decorated function is a method. Will
          add one to the number of allowed positional args to account for
          ``self``. Defaults to True.
    """

    template = (
        'Calls to {{fn}}(...) with{arg_text} positional args are deprecated.'
        ' Please specify them as keyword arguments instead.'
    )
    text = ' more than {}'.format(allowed_positional) if allowed_positional else ''
    warn_text = template.format(arg_text=text)
    if is_method:
        allowed_positional += 1

    def deprecated_args(fn):
        @functools.wraps(fn)
        def wraps(*args, **kwargs):
            if len(args) > allowed_positional:
                warnings.warn(
                    warn_text.format(fn=fn.__qualname__),
                    DeprecatedWarning,
                    stacklevel=2,
                )
            return fn(*args, **kwargs)

        return wraps

    return deprecated_args
