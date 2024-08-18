import glob
import io
import os
from os import path
import platform
import re

from setuptools import setup

try:
    from Cython.Build import build_ext as _cy_build_ext
    from Cython.Distutils.extension import Extension as _cy_Extension

    HAS_CYTHON = True
except ImportError:
    _cy_build_ext = _cy_Extension = None
    HAS_CYTHON = False

DISABLE_EXTENSION = bool(os.environ.get('FALCON_DISABLE_CYTHON'))
IS_CPYTHON = platform.python_implementation() == 'CPython'

MYDIR = path.abspath(os.path.dirname(__file__))


if HAS_CYTHON and IS_CPYTHON and not DISABLE_EXTENSION:
    assert _cy_Extension is not None
    assert _cy_build_ext is not None

    def list_modules(dirname, pattern):
        filenames = glob.glob(path.join(dirname, pattern))

        module_names = []
        for name in filenames:
            module, ext = path.splitext(path.basename(name))
            if module != '__init__':
                module_names.append((module, ext))

        return module_names

    package_names = [
        'falcon',
        'falcon.cyutil',
        'falcon.media',
        'falcon.routing',
        'falcon.util',
        'falcon.vendor.mimeparse',
    ]

    modules_to_exclude = [
        # NOTE(kgriffs): Cython does not handle dynamically-created async
        #   methods correctly.
        # NOTE(vytas,kgriffs): We have to also avoid cythonizing several
        #   other functions that might make it so that the framework
        #   can not recognize them as coroutine functions.
        #
        #   See also:
        #
        #       * https://github.com/cython/cython/issues/2273
        #       * https://bugs.python.org/issue38225
        #
        # NOTE(vytas): It is pointless to cythonize reader.py, since cythonized
        #   Falcon is using reader.pyx instead.
        'falcon.hooks',
        'falcon.responders',
        'falcon.util.reader',
        'falcon.util.sync',
    ]

    cython_package_names = ('falcon.cyutil',)
    # NOTE(vytas): Now that all our codebase is Python 3.7+, specify the
    #   Python 3 language level for Cython as well to avoid any surprises.
    cython_directives = {'language_level': '3', 'annotation_typing': False}

    ext_modules = [
        _cy_Extension(
            package + '.' + module,
            sources=[path.join(*(package.split('.') + [module + ext]))],
            cython_directives=cython_directives,
            optional=True,
        )
        for package in package_names
        for module, ext in list_modules(
            path.join(MYDIR, *package.split('.')),
            ('*.pyx' if package in cython_package_names else '*.py'),
        )
        if (package + '.' + module) not in modules_to_exclude
    ]

    cmdclass = {'build_ext': _cy_build_ext}
else:
    ext_modules = []
    cmdclass = {}


def load_description():
    in_patron_list = False
    in_patron_replacement = False
    in_raw = False

    description_lines = []

    # NOTE(kgriffs): PyPI does not support the raw directive
    for readme_line in io.open('README.rst', 'r', encoding='utf-8'):
        # NOTE(vytas): The patron list largely builds upon raw sections
        if readme_line.startswith('.. Patron list starts'):
            in_patron_list = True
            in_patron_replacement = True
            continue
        elif in_patron_list:
            if not readme_line.strip():
                in_patron_replacement = False
            elif in_patron_replacement:
                description_lines.append(readme_line.lstrip())
            if readme_line.startswith('.. Patron list ends'):
                in_patron_list = False
            continue
        elif readme_line.startswith('.. raw::'):
            in_raw = True
        elif in_raw:
            if readme_line and not re.match(r'\s', readme_line):
                in_raw = False

        if not in_raw:
            description_lines.append(readme_line)

    return ''.join(description_lines)


def status_msgs(*msgs):
    print('*' * 75, *msgs, '*' * 75, sep='\n')


setup(
    long_description=load_description(),
    long_description_content_type = 'text/x-rst',
    cmdclass=cmdclass,
    ext_modules=ext_modules,
)
