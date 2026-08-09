#!/usr/bin/env python3
"""Verify trace-context propagation through HTTP responses and Jaeger."""

import argparse
import json
import sys
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


JAEGER_URL = "http://localhost:16686"
CHAINS = {
    "on": {
        "gateway": "http://localhost:8001/work",
        "services": ("gateway-on", "orders-on", "payments-on"),
    },
    "off": {
        "gateway": "http://localhost:8002/work",
        "services": ("gateway-off", "orders-off", "payments-off"),
    },
}


def get_json(url, timeout=3):
    with urlopen(url, timeout=timeout) as response:
        return json.load(response)


def wait_until_ready(timeout=90):
    deadline = time.monotonic() + timeout
    pending = {
        "Jaeger": f"{JAEGER_URL}/api/services",
        "propagation ON gateway": "http://localhost:8001/health",
        "propagation OFF gateway": "http://localhost:8002/health",
    }
    while pending and time.monotonic() < deadline:
        for name, url in list(pending.items()):
            try:
                get_json(url)
                del pending[name]
            except (OSError, URLError, ValueError):
                pass
        if pending:
            time.sleep(1)
    if pending:
        raise RuntimeError("not ready: " + ", ".join(pending))


def flatten_chain(response):
    chain = []
    current = response
    while current:
        chain.append(current)
        current = current.get("downstream")
    return chain


def send_requests(mode, count):
    responses = []
    for _ in range(count):
        responses.append(get_json(CHAINS[mode]["gateway"], timeout=10))
    return responses


def query_service(service, started_us):
    query = urlencode(
        {"service": service, "start": started_us, "end": int(time.time() * 1_000_000), "limit": 1000}
    )
    payload = get_json(f"{JAEGER_URL}/api/traces?{query}", timeout=10)
    return payload.get("data", [])


def collect_traces(mode, started_us):
    traces = {}
    for service in CHAINS[mode]["services"]:
        for item in query_service(service, started_us):
            traces[item["traceID"]] = item
    return traces


def trace_services(trace_item):
    return {
        process["serviceName"]
        for process in trace_item.get("processes", {}).values()
    }


def wait_for_traces(mode, started_us, expected, timeout=30):
    deadline = time.monotonic() + timeout
    traces = {}
    while time.monotonic() < deadline:
        traces = collect_traces(mode, started_us)
        if len(traces) >= expected:
            return traces
        time.sleep(0.5)
    return traces


def validate_response(mode, responses):
    for index, response in enumerate(responses, 1):
        chain = flatten_chain(response)
        if len(chain) != 3:
            raise AssertionError(f"{mode} request {index}: expected 3 hops, got {len(chain)}")
        trace_ids = [hop["trace_id"] for hop in chain]
        downstream_headers = [hop["received_traceparent"] for hop in chain[1:]]
        if mode == "on":
            if len(set(trace_ids)) != 1 or not all(downstream_headers):
                raise AssertionError(f"ON chain is broken: {trace_ids}")
        elif len(set(trace_ids)) != 3 or any(downstream_headers):
            raise AssertionError(f"OFF chain unexpectedly propagated context: {trace_ids}")
    return flatten_chain(responses[0])


def validate_jaeger(mode, traces, request_count):
    expected_trace_count = request_count if mode == "on" else request_count * 3
    expected_span_count = request_count * 5
    span_count = sum(len(item.get("spans", [])) for item in traces.values())
    expected_services = set(CHAINS[mode]["services"])

    if len(traces) != expected_trace_count:
        raise AssertionError(
            f"{mode}: expected {expected_trace_count} traces, got {len(traces)}"
        )
    if span_count != expected_span_count:
        raise AssertionError(
            f"{mode}: expected {expected_span_count} spans, got {span_count}"
        )
    for item in traces.values():
        services = trace_services(item)
        if mode == "on" and services != expected_services:
            raise AssertionError(f"ON trace has incomplete services: {services}")
        if mode == "off" and len(services) != 1:
            raise AssertionError(f"OFF trace connected multiple services: {services}")
    return span_count


def print_chain(label, chain):
    print(label)
    for hop in chain:
        received = "yes" if hop["received_traceparent"] else "no"
        print(
            f"  {hop['service']:<13} trace_id={hop['trace_id']} "
            f"received_traceparent={received}"
        )


def main():
    parser = argparse.ArgumentParser(description="Verify W3C trace context propagation")
    parser.add_argument("--requests", type=int, default=3)
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be at least 1")

    try:
        wait_until_ready()
        started_us = int(time.time() * 1_000_000) - 1_000_000
        on_responses = send_requests("on", args.requests)
        off_responses = send_requests("off", args.requests)

        on_chain = validate_response("on", on_responses)
        off_chain = validate_response("off", off_responses)
        print_chain("[PASS] propagation ON: all hops keep one trace ID", on_chain)
        print_chain("[PASS] propagation OFF: every hop starts a new trace ID", off_chain)

        on_traces = wait_for_traces("on", started_us, args.requests)
        off_traces = wait_for_traces("off", started_us, args.requests * 3)
        on_spans = validate_jaeger("on", on_traces, args.requests)
        off_spans = validate_jaeger("off", off_traces, args.requests)

        print("[PASS] Jaeger")
        print(f"  ON : {args.requests} requests -> {len(on_traces)} traces, {on_spans} spans")
        print(f"  OFF: {args.requests} requests -> {len(off_traces)} traces, {off_spans} spans")
        print(f"  UI : {JAEGER_URL}")
        print("\nConclusion: propagation changes the edges, not the number of spans.")
    except (AssertionError, RuntimeError, OSError, URLError, ValueError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
