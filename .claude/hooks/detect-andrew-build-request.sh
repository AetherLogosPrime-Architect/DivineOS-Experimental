#!/usr/bin/env bash
# UserPromptSubmit hook wrapper — routes to detect_andrew_build_request.py.
# See that file's docstring for design; council-85dc063549cc; prereg-45e0aa113e3a.
exec python "$(dirname "$0")/detect_andrew_build_request.py"
