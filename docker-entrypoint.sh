#!/bin/sh
set -eu

exec uvicorn main:app --host 0.0.0.0 --port 8014
