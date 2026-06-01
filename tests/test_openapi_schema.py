"""Regression tests for the stdlib REST API OpenAPI schema."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

from texthumanize.api import (
    OPENAPI_JSON_PATH,
    PUBLIC_ENDPOINTS,
    TextHumanizeHandler,
    get_openapi_schema,
)


def _make_handler(path: str):
    handler = MagicMock(spec=TextHumanizeHandler)
    handler.path = path
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.client_address = ("127.0.0.1", 12345)
    return handler


def test_openapi_schema_covers_public_endpoints():
    schema = get_openapi_schema()

    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["title"] == "TextHumanize REST API"
    assert schema["components"]["schemas"]["HumanizeRequest"]

    for path in [*PUBLIC_ENDPOINTS, "/", "/health", OPENAPI_JSON_PATH]:
        assert path in schema["paths"]

    for path in PUBLIC_ENDPOINTS:
        assert "post" in schema["paths"][path]
        assert "requestBody" in schema["paths"][path]["post"]
        assert "200" in schema["paths"][path]["post"]["responses"]

    assert schema["paths"]["/health"]["get"]["operationId"] == "getHealth"
    assert schema["paths"][OPENAPI_JSON_PATH]["get"]["operationId"] == "getOpenApiSchema"


def test_get_openapi_json_endpoint_serves_schema():
    handler = _make_handler(OPENAPI_JSON_PATH)

    TextHumanizeHandler.do_GET(handler)

    handler.send_response.assert_called_once_with(200)
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["openapi"] == "3.1.0"
    assert "/humanize" in payload["paths"]
    assert payload["components"]["schemas"]["ErrorResponse"]


def test_root_and_health_advertise_openapi_schema():
    for path in ("/", "/health"):
        handler = _make_handler(path)
        TextHumanizeHandler.do_GET(handler)
        payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert payload["openapi"] == OPENAPI_JSON_PATH
        assert "/sse/humanize" in payload["endpoints"]
