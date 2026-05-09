#!/bin/sh
set -eu

shutdown() {
  kill "$consumer_pid" "$api_pid" 2>/dev/null || true
  wait "$consumer_pid" "$api_pid" 2>/dev/null || true
}

trap shutdown INT TERM

python consumer.py &
consumer_pid="$!"

uvicorn main:app --host 0.0.0.0 --port 8014 &
api_pid="$!"

while :; do
  if ! kill -0 "$consumer_pid" 2>/dev/null; then
    set +e
    wait "$consumer_pid"
    exit_code="$?"
    set -e
    break
  fi

  if ! kill -0 "$api_pid" 2>/dev/null; then
    set +e
    wait "$api_pid"
    exit_code="$?"
    set -e
    break
  fi

  sleep 2
done

shutdown
exit "$exit_code"
