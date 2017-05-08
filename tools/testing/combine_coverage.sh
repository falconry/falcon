#!/usr/bin/env bash

coverage combine .coverage_data
coverage html -d .coverage_html
coverage report
