import glob
import imp
import io
import os
from os import path
import sys

from setuptools import Extension, find_packages, setup

MYDIR = path.abspath(os.path.dirname(__file__))

VERSION = imp.load_source('version', path.join('.', 'falcon', 'version.py'))
VERSION = VERSION.__version__

# NOTE(kgriffs): python-mimeparse is better-maintained fork of mimeparse
REQUIRES = ['six>=1.4.0', 'python-mimeparse>=1.5.2']

JYTHON = 'java' in sys.platform

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

if PYPY or JYTHON:
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

    package_names = ['falcon', 'falcon.util', 'falcon.routing']
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
        'Programming Language :: Python :: Implementation :: Jython',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
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
    setup_requires=['pytest-runner'],
    cmdclass=cmdclass,
    ext_modules=ext_modules,
    tests_require=['ddt', 'testtools', 'requests', 'pyyaml', 'pytest'],
    entry_points={
        'console_scripts': [
            'falcon-bench = falcon.cmd.bench:main',
            'falcon-print-routes = falcon.cmd.print_routes:main'
        ]
    }
)
