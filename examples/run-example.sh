#!/bin/sh
# Demo: check the good file (passes), then the bad-format file and
# the duplicates file (both fail, on purpose). The failing runs
# exit 1, which is the expected result — the script ends with exit 0
# so it can be run as a demo.
cd "$(dirname "$0")/.."
python3 src/dotenv_format_checker.py examples/good.env
python3 src/dotenv_format_checker.py examples/bad-format.env || true
python3 src/dotenv_format_checker.py examples/duplicates.env || true
