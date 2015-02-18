#!/usr/bin/env bash

#python setup.py bdist_egg upload
python setup.py sdist --formats=gztar,zip upload --sign
# python setup.py bdist_wheel upload
