#!/usr/bin/env bash

# Copyright 2016 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

VENV_NAME=tmp-falcon-build
BUILD_DIR=./build
DIST_DIR=./dist
PY3_VERSION=3.8.0

#----------------------------------------------------------------------
# Helpers
#----------------------------------------------------------------------

# Args: (python_version)
_open_env() {
    local PY_VERSION=$1

    pyenv install -s $PY_VERSION
    pyenv virtualenv $PY_VERSION $VENV_NAME
    pyenv shell $VENV_NAME

    pip install -q --upgrade pip
    pip install -q --upgrade wheel twine

    echo
}

# Args: ()
_close_env() {
    rm -rf $DIST_PATH
    pyenv shell system
    pyenv uninstall -f $VENV_NAME
}

# Args: (message)
_echo_task() {
    echo
    echo "# ----------------------------------------------------------"
    echo "# $1"
    echo "# ----------------------------------------------------------"

}

#----------------------------------------------------------------------
# Prerequisites
#----------------------------------------------------------------------

# Setup pyenv
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

#----------------------------------------------------------------------
# Start with a clean slate
#----------------------------------------------------------------------

_echo_task "Cleaning up old artifacts"

tools/clean.sh .

rm -rf $BUILD_DIR
rm -rf $DIST_DIR

pyenv shell system
pyenv uninstall -f $VENV_NAME

#----------------------------------------------------------------------
# Source distribution
#----------------------------------------------------------------------

_echo_task "Building source distribution"
_open_env $PY3_VERSION

python setup.py sdist -d $DIST_DIR

_close_env

#----------------------------------------------------------------------
# Universal wheel - do not include Cython, note in README
#----------------------------------------------------------------------

_echo_task "Building universal wheel"
_open_env $PY3_VERSION

python setup.py bdist_wheel -d $DIST_DIR

_close_env

#----------------------------------------------------------------------
# README validation
#----------------------------------------------------------------------

_echo_task "Checking that README will render on PyPI"
_open_env $PY3_VERSION

twine check $DIST_DIR/*

_close_env
