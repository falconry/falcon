import glob
import imp
import io
import os
from os import path
from setuptools import setup, find_packages, Extension
import sys

MYDIR = path.abspath(os.path.dirname(__file__))

VERSION = imp.load_source('version', path.join('.', 'falcon', 'version.py'))
VERSION = VERSION.__version__

# NOTE(kgriffs): python-mimeparse is newer than mimeparse, supports Py3
# TODO(kgriffs): Fork and optimize/modernize python-mimeparse
REQUIRES = ['six', 'python-mimeparse']

PYPY = True
CYTHON = False
try:
    sys.pypy_version_info
except AttributeError:
    PYPY = False

if not PYPY:
    try:
        from Cython.Distutils import build_ext
        CYTHON = True
    except ImportError:
        print('\nWARNING: Cython not installed. '
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

    ext_modules = [
        Extension('falcon.' + ext, [path.join('falcon', ext + '.py')])
        for ext in list_modules(path.join(MYDIR, 'falcon'))]

    ext_modules += [
        Extension('falcon.util.' + ext,
                  [path.join('falcon', 'util', ext + '.py')])

        for ext in list_modules(path.join(MYDIR, 'falcon', 'util'))]

    cmdclass = {'build_ext': build_ext}

else:
    cmdclass = {}
    ext_modules = []

setup(
    name='falcon',
    version=VERSION,
    description='An unladen web framework for building APIs and app backends.',
    long_description=io.open('README.rst', 'r', encoding='utf-8').read(),
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='wsgi web api framework rest http cloud',
    author='Kurt Griffiths',
    author_email='mail@kgriffs.com',
    url='http://falconframework.org',
    license='Apache 2.0',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRES,
    setup_requires=[],
    cmdclass=cmdclass,
    ext_modules=ext_modules,
    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'falcon-bench = falcon.cmd.bench:main'
        ]
    }
)
