#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "$@"

activate_venv () {
  . $SCRIPT_DIR/.venv/bin/activate
}

start () {
  $(which python3) $SCRIPT_DIR/boneGPT.py "$@"
}

activate_venv
start "$@"