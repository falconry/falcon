#!/bin/sh

echo "Python Version:\n=================="
python --version

echo "Installed Packages:\n=================="
pip list

echo "\nBenchmark:\n=================="
falcon-bench
