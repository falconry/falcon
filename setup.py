from os import path
from setuptools import setup, find_packages, Extension

try:
    with open(path.join(path.dirname(__file__),
                        "falcon",
                        "version.py")) as version_file:
        exec(version_file.read())
except IOError:
    print('\nWARNING: version.py file is missing.\n')

try:
    from Cython.Distutils import build_ext
    with_cython = True
except ImportError:
    print('\nWARNING: Cython not installed. '
          'Falcon modules WILL NOT be compiled.\n')
    with_cython = False

if with_cython:
    ext_names = (
        'api',
        'api_helpers',
        'request',
        'request_helpers',
        'response',
        'response_helpers',
        'responders',
        'http_error',
        'exceptions'
    )

    cmdclass = {'build_ext': build_ext}
    ext_modules = [
        Extension('falcon.' + ext, [path.join('falcon', ext + '.py')])
        for ext in ext_names]
else:
    cmdclass = {}
    ext_modules = []


setup(
    name='falcon',
    version=version,
    description='A fast micro-framework for building cloud APIs.',
    long_description=None,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
    ],
    keywords='wsgi web api framework rest http cloud',
    author='Kurt Griffiths',
    author_email='mail@kgriffs.com',
    url='https://github.com/racker/falcon',
    license='Apache 2.0',
    packages=find_packages(exclude=['bench', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=['six', 'testtools'],
    cmdclass=cmdclass,
    ext_modules=ext_modules
)
