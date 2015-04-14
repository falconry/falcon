#!/usr/bin/env bash

find $1 \( -name '*.c' -or -name '*.so' -or -name '*.pyc' \) -delete
