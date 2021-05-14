import glob
import importlib
import io
import os
from os import path
import re
import sys

from setuptools import Extension, find_packages, setup

MYDIR = path.abspath(os.path.dirname(__file__))

with open(path.join(path.dirname(__file__), 'falcon', 'version.py')) as v_file:
    VERSION = (
        re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
        .match(v_file.read())
        .group(1)
    )

REQUIRES = []

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

if PYPY:
    CYTHON = False
else:
    try:
        from Cython.Distutils import build_ext
        CYTHON = True
    except ImportError:
        CYTHON = False


class BuildFailed(Exception):
    pass


def get_cython_options():
    # from sqlalchemy setup.py
    from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError
    ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)
    if sys.platform == 'win32':
        # Work around issue https://github.com/pypa/setuptools/issues/1902
        ext_errors += (IOError, TypeError)

    class ve_build_ext(build_ext):
        # This class allows Cython building to fail.

        def run(self):
            try:
                super().run()
            except DistutilsPlatformError:
                raise BuildFailed()

        def build_extension(self, ext):
            try:
                super().build_extension(ext)
            except ext_errors as e:
                raise BuildFailed() from e
            except ValueError as e:
                # this can happen on Windows 64 bit, see Python issue 7511
                if "'path'" in str(e):
                    raise BuildFailed() from e
                raise

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

    cython_package_names = frozenset([
        'falcon.cyutil',
    ])

    ext_modules = [
        Extension(
            package + '.' + module,
            [path.join(*(package.split('.') + [module + ext]))]
        )
        for package in package_names
        for module, ext in list_modules(
            path.join(MYDIR, *package.split('.')),
            ('*.pyx' if package in cython_package_names else '*.py'))
        if (package + '.' + module) not in modules_to_exclude
    ]

    # NOTE(vytas): Now that all our codebase is Python 3.5+, specify the
    #   Python 3 language level for Cython as well to avoid any surprises.
    for ext_mod in ext_modules:
        ext_mod.cython_directives = {'language_level': '3'}

    cmdclass = {'build_ext': ve_build_ext}
    return cmdclass, ext_modules


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


def run_setup(CYTHON):
    if CYTHON:
        cmdclass, ext_modules = get_cython_options()
    else:
        cmdclass, ext_modules = {}, []

    setup(
        name='falcon',
        version=VERSION,
        description='An unladen web framework for building APIs and app backends.',
        long_description=load_description(),
        long_description_content_type='text/x-rst',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Web Environment',
            'Natural Language :: English',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: POSIX',
            'Topic :: Internet :: WWW/HTTP :: WSGI',
            'Topic :: Software Development :: Libraries :: Application Frameworks',
            'Programming Language :: Python',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
        ],
        keywords='wsgi web api framework rest http cloud',
        author='Kurt Griffiths',
        author_email='mail@kgriffs.com',
        url='https://falconframework.org',
        license='Apache 2.0',
        packages=find_packages(exclude=['tests']),
        include_package_data=True,
        zip_safe=False,
        python_requires='>=3.5',
        install_requires=REQUIRES,
        cmdclass=cmdclass,
        ext_modules=ext_modules,
        tests_require=['testtools', 'requests', 'pyyaml', 'pytest', 'pytest-runner'],
        entry_points={
            'console_scripts': [
                'falcon-bench = falcon.cmd.bench:main',
                'falcon-inspect-app = falcon.cmd.inspect_app:main',
                'falcon-print-routes = falcon.cmd.inspect_app:route_main',
            ]
        }
    )


def status_msgs(*msgs):
    print('*' * 75, *msgs, '*' * 75, sep='\n')


if not CYTHON:
    run_setup(False)
    if not PYPY:
        status_msgs('Cython compilation not supported in this environment')
else:
    try:
        run_setup(True)
    except BuildFailed as exc:
        status_msgs(
            exc.__cause__,
            'Cython compilation could not be completed, speedups are not enabled.',
            'Failure information, if any, is above.',
            'Retrying the build without the C extension now.'
        )

        run_setup(False)

        status_msgs(
            'Cython compilation could not be completed, speedups are not enabled.',
            'Pure-Python build succeeded.'
        )
