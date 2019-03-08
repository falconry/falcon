import glob
import imp
import io
import os
from os import path
import re
import sys

from setuptools import Extension, find_packages, setup

MYDIR = path.abspath(os.path.dirname(__file__))

VERSION = imp.load_source('version', path.join('.', 'falcon', 'version.py'))
VERSION = VERSION.__version__

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
        # TODO(kgriffs): pip now ignores all output, so the user
        # may not see this message. See also:
        #
        #   https://github.com/pypa/pip/issues/2732
        #
        print('\nNOTE: Cython not installed. '
              'Falcon will still work fine, but may run '
              'a bit slower.\n')
        CYTHON = False

if CYTHON:
    def list_modules(dirname):
        filenames = glob.glob(path.join(dirname, '*.py'))

        module_names = []
        for name in filenames:
            module, ext = path.splitext(path.basename(name))
            if module != '__init__':
                module_names.append(module)

        return module_names

    package_names = [
        'falcon',
        'falcon.media',
        'falcon.routing',
        'falcon.util',
        'falcon.vendor.mimeparse',
    ]
    ext_modules = [
        Extension(
            package + '.' + module,
            [path.join(*(package.split('.') + [module + '.py']))]
        )
        for package in package_names
        for module in list_modules(path.join(MYDIR, *package.split('.')))
    ]

    cmdclass = {'build_ext': build_ext}

else:
    cmdclass = {}
    ext_modules = []


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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='wsgi web api framework rest http cloud',
    author='Kurt Griffiths',
    author_email='mail@kgriffs.com',
    url='https://falconframework.org',
    license='Apache 2.0',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    install_requires=REQUIRES,
    cmdclass=cmdclass,
    ext_modules=ext_modules,
    tests_require=['testtools', 'requests', 'pyyaml', 'pytest', 'pytest-runner'],
    entry_points={
        'console_scripts': [
            'falcon-bench = falcon.cmd.bench:main',
            'falcon-print-routes = falcon.cmd.print_routes:main'
        ]
    }
)
