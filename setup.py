from setuptools import setup, find_packages

import falcon.version


setup(
    name='falcon',
    version=falcon.version,
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
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ],
    keywords='wsgi web api framework rest http cloud',
    author='Kurt Griffiths',
    author_email='mail@kgriffs.com',
    url='https://github.com/racker/falcon',
    license='Apache 2.0',
    packages=find_packages(exclude=['bench', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=['six'],

    test_suite='nose.collector',
    tests_require='nose'
)
