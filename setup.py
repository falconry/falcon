from setuptools import setup, find_packages
import os

import falcon

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.md')).read()

install_requires = [
    'python-statsd>=1.5.7'
]

setup(
    name='falcon',
    version=falcon.version,
    description="Falcon is a fast micro-framework for building cloud APIs.",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Topic :: Software Development :: Libraries :: Application Frameworks"
    ],
    keywords='wsgi web api framework rest http',
    author='Kurt Griffiths',
    author_email='kgriffs@me.com',
    url='https://github.com/racker/falcon',
    license='Apache 2.0',
    packages=find_packages('falcon'),
    package_dir={'': 'falcon'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires
)
