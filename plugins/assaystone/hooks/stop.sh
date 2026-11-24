#!/usr/bin/env bash
set -u

# A Stop hook must never break the session. If the CLI is not installed, fail open.
if ! command -v assaystone >/dev/null 2>&1; then
  exit 0
fi

exec assaystone hook claude-code
