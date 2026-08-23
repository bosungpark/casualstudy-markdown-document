#!/usr/bin/env sh
set -eu

darkhttpd /srv/http --port 8080 --addr 0.0.0.0 &
http_pid=$!

cleanup() {
  kill "$http_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
dnsmasq --keep-in-foreground --conf-file=/etc/dnsmasq.conf
