#!/bin/bash

set -e

# TODO find way to install dependencies from manifest.json directly
# Create a local venv in the workspace and install requirements
PYTHON="/usr/local/bin/python3.13"
if [ ! -d "dev/.venv" ]; then
  $PYTHON -m venv dev/.venv
fi
. dev/.venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
