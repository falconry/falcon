#!/bin/sh

echo "Installed Packages:\n=================="
pip list

echo "\nBenchmark:\n=================="
falcon-bench
