import glob
import os
from os import path
import platform

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
        'falcon.inspect',
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


setup(cmdclass=cmdclass, ext_modules=ext_modules)
