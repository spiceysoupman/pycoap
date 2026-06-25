#!/bin/bash
uv --version || (echo "UV package manager is missing. Its recommended to" && exit)
uv venv .venv
echo "Upgrading and installing packages"
uv pip install -p ./.venv --upgrade "aiocoap[all]"
uv pip install -p ./.venv --upgrade "cbor2"
uv pip install -p ./.venv --upgrade "cbor_diag"