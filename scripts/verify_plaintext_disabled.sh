#!/usr/bin/env bash
set -euo pipefail

if docker exec smarthouse-mqtt sh -lc "mosquitto_pub -h localhost -p 1883 -u smarthouse -P smarthouse-mqtt-pass -t platform/home01/plaintextcheck/event -m '{\"event\":\"plaintext_try\"}'" >/tmp/plaintext_try.log 2>&1; then
  echo "PLAINTEXT_UNEXPECTED=success"
else
  echo "PLAINTEXT_EXPECTED=failure"
fi
