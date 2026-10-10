"""Loopback-only adapter for a locally hosted OpenAI-compatible chat-completions server."""

import ipaddress
import json
from math import isfinite
import time
import urllib.request
from urllib.parse import urlsplit

from src.agents.provider import ProviderLocation

from .provider import ProviderFailure


DEFAULT_URL = "http://127.0.0.1:11434/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
FAILURE_MESSAGE = "The local mediation provider is unavailable."


def validate_loopback_url(url):
    """Accept http(s) URLs on localhost/127.0.0.0/8/::1 only. Messages never echo the URL."""
    if type(url) is not str or not url or len(url) > 2_048 or not url.isprintable():
        raise ValueError("The mediation endpoint must be a loopback http(s) URL.")
    try:
        parts = urlsplit(url)
        parts.port  # Raises ValueError for an invalid port.
    except ValueError:
        raise ValueError("The mediation endpoint must be a loopback http(s) URL.") from None
    host = parts.hostname
    if parts.scheme not in ("http", "https") or host is None or parts.username or parts.password:
        raise ValueError("The mediation endpoint must be a loopback http(s) URL.")
    if host != "localhost":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ValueError("The mediation endpoint must be a loopback http(s) URL.")
    return url


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect could forward financial facts away from loopback.
        raise OSError("Redirects are refused by the mediation provider.")


def loopback_opener():
    # An empty ProxyHandler replaces the environment-driven default proxies.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirect())


def _post(url, body, headers, timeout):
    # The socket timeout bounds each operation; the deadline bounds the whole call
    # so a server trickling bytes cannot hold the conversation open indefinitely.
    deadline = time.monotonic() + timeout
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    reply = bytearray()
    with loopback_opener().open(request, timeout=timeout) as response:
        while len(reply) <= MAX_RESPONSE_BYTES:
            if time.monotonic() > deadline:
                raise TimeoutError("Mediation provider deadline exceeded.")
            chunk = response.read1(8_192)
            if not chunk:
                break
            reply.extend(chunk)
    return bytes(reply)


class LocalHTTPProvider:
    """One POST per call: no retries, credentials, logging or transcript."""

    location = ProviderLocation.LOCAL

    def __init__(self, *, url=DEFAULT_URL, model, timeout=DEFAULT_TIMEOUT_SECONDS, transport=None):
        self._url = validate_loopback_url(url)
        if type(model) is not str or not 0 < len(model) <= 200 or not model.isprintable():
            raise ValueError("The mediation model name must be printable text of at most 200 characters.")
        if (type(timeout) not in (int, float) or not isfinite(timeout)
                or not 0 < timeout <= MAX_TIMEOUT_SECONDS):
            raise ValueError("The mediation timeout must be between 0 and 120 seconds.")
        self._model = model
        self._timeout = timeout
        self._transport = _post if transport is None else transport

    def complete(self, request):
        body = json.dumps({
            "model": self._model,
            "messages": [{"role": "system", "content": request.system},
                         {"role": "user", "content": request.user}],
            "temperature": 0,
            "stream": False,
            "response_format": ({"type": "json_object"} if request.schema is None else
                                {"type": "json_schema",
                                 "json_schema": {"name": request.task, "strict": True,
                                                 "schema": request.schema}}),
        }, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_REQUEST_BYTES:
            raise ProviderFailure(FAILURE_MESSAGE)
        try:
            reply = self._transport(self._url, body, {"Content-Type": "application/json"},
                                    self._timeout)
            if type(reply) is not bytes or len(reply) > MAX_RESPONSE_BYTES:
                raise ValueError("invalid reply size")
            content = json.loads(reply)["choices"][0]["message"]["content"]
            if type(content) is not str or len(content) > request.max_output_characters:
                raise ValueError("invalid content")
        except Exception:
            # Exception text may contain hosts, paths or tokens; none of it is kept.
            raise ProviderFailure(FAILURE_MESSAGE) from None
        return content
