import logging
import os

import requests
from flask import Flask, jsonify, request
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


SERVICE_NAME = os.environ["SERVICE_NAME"]
NEXT_URL = os.getenv("NEXT_URL")
PROPAGATION = os.getenv("PROPAGATION", "on").lower()
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://jaeger:4318/v1/traces"
)


class NoOpTextMapPropagator:
    """Disable both inbound extraction and outbound header injection."""

    def inject(self, carrier, context=None, setter=None):
        return None

    def extract(self, carrier, context=None, getter=None):
        return context if context is not None else Context()

    @property
    def fields(self):
        return set()


if PROPAGATION == "on":
    set_global_textmap(TraceContextTextMapPropagator())
elif PROPAGATION == "off":
    set_global_textmap(NoOpTextMapPropagator())
else:
    raise ValueError("PROPAGATION must be either 'on' or 'off'")

provider = TracerProvider(
    resource=Resource.create({"service.name": SERVICE_NAME}),
    sampler=ParentBased(ALWAYS_ON),
)
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint=OTLP_ENDPOINT),
        schedule_delay_millis=200,
        max_export_batch_size=64,
    )
)
trace.set_tracer_provider(provider)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app, excluded_urls="health")
RequestsInstrumentor().instrument()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(SERVICE_NAME)


def current_trace_context():
    span_context = trace.get_current_span().get_span_context()
    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/work")
def work():
    context = current_trace_context()
    received_traceparent = request.headers.get("traceparent")
    logger.info(
        "service=%s propagation=%s trace_id=%s received_traceparent=%s",
        SERVICE_NAME,
        PROPAGATION,
        context["trace_id"],
        received_traceparent or "-",
    )

    result = {
        "service": SERVICE_NAME,
        "propagation": PROPAGATION,
        "received_traceparent": received_traceparent,
        **context,
    }

    if NEXT_URL:
        downstream_response = requests.get(NEXT_URL, timeout=5)
        downstream_response.raise_for_status()
        result["downstream"] = downstream_response.json()

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
