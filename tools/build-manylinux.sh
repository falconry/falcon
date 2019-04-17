#!/bin/bash

# DOCKER_IMAGE=quay.io/pypa/manylinux1_x86_64
#
# DOCKER_IMAGE=quay.io/pypa/manylinux1_i686
# PRE_CMD=linux32
#
# docker pull $DOCKER_IMAGE
# docker run --rm -v `pwd`:/io $DOCKER_IMAGE $PRE_CMD /io/tools/build-manylinux.sh

set -e -x

# Compile wheels
for PYBIN in /opt/python/*/bin; do
    "${PYBIN}/pip" install cython
    "${PYBIN}/pip" wheel /io/ -w dist/
done

# Bundle external shared libraries into the wheels
for whl in dist/*.whl; do
    auditwheel repair "$whl" -w /io/dist/
done

# Install packages and test
for PYBIN in /opt/python/*/bin/; do
    "${PYBIN}/pip" install falcon --no-index -f /io/dist
    (cd "$HOME"; "${PYBIN}/falcon-bench" -b falcon -t 1)
done
