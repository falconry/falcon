#!/usr/bin/env bash

coverage combine
coverage html -d .coverage_html
coverage report
