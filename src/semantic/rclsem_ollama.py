#!/usr/bin/env python3
"""Policy-enforcing, dependency-free client for a local Ollama service."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import math
import socket
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://127.0.0.1:11434"


class OllamaError(Exception):
    """Base error raised by the Ollama adapter."""


class OllamaPolicyError(OllamaError):
    """Raised before a request that violates local-only policy."""


class OllamaConnectionError(OllamaError):
    """Raised when the configured local Ollama service cannot be reached."""


class OllamaAPIError(OllamaError):
    """Raised when Ollama responds with an HTTP or API error."""


class OllamaProtocolError(OllamaError):
    """Raised when an Ollama response violates the expected contract."""


@dataclass(frozen=True)
class OllamaPolicy:
    """Network and model restrictions applied before every Ollama request."""

    require_loopback: bool = True
    allow_cloud_models: bool = False

    def validate_endpoint(self, endpoint: str) -> str:
        if not isinstance(endpoint, str) or not endpoint:
            raise OllamaPolicyError("Ollama endpoint must be a non-empty URL")
        parsed = urlparse(endpoint)
        if parsed.scheme != "http":
            raise OllamaPolicyError("local Ollama endpoint must use plain HTTP")
        if parsed.username or parsed.password:
            raise OllamaPolicyError("credentials are not permitted in the Ollama endpoint")
        try:
            port = parsed.port
        except ValueError as ex:
            raise OllamaPolicyError("Ollama endpoint has an invalid port") from ex
        if not parsed.hostname or port is None:
            raise OllamaPolicyError("Ollama endpoint must include a host and port")
        if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
            raise OllamaPolicyError("Ollama endpoint must not include a path, query, or fragment")
        if self.require_loopback and not _is_loopback_host(parsed.hostname):
            raise OllamaPolicyError("Ollama endpoint must resolve to the local machine")
        return endpoint.rstrip("/")

    def validate_model(self, model: str) -> None:
        if not isinstance(model, str) or not model.strip():
            raise OllamaPolicyError("model name must be a non-empty string")
        lowered = model.strip().lower()
        if not self.allow_cloud_models and (
            lowered.endswith("-cloud") or ":cloud" in lowered or "-cloud:" in lowered
        ):
            raise OllamaPolicyError(f"cloud model is disabled by local-only policy: {model}")


def _is_loopback_host(host: str) -> bool:
    lowered = host.rstrip(".").lower()
    if lowered == "localhost":
        return True
    try:
        return ipaddress.ip_address(lowered).is_loopback
    except ValueError:
        # Do not resolve arbitrary names: DNS itself would expand the trust boundary.
        return False


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int
    digest: str
    parameter_size: str = ""
    quantization: str = ""


class OllamaClient:
    """Small synchronous client for the Ollama endpoints Recoll Next uses."""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        *,
        timeout: float = 10.0,
        policy: Optional[OllamaPolicy] = None,
    ):
        self.policy = policy or OllamaPolicy()
        self.endpoint = self.policy.validate_endpoint(endpoint)
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout

    def list_models(self) -> List[OllamaModel]:
        response = self._request_json("GET", "/api/tags")
        raw_models = response.get("models")
        if not isinstance(raw_models, list):
            raise OllamaProtocolError("Ollama model response has no models array")
        models: List[OllamaModel] = []
        for position, raw_model in enumerate(raw_models):
            if not isinstance(raw_model, dict):
                raise OllamaProtocolError(f"model at position {position} is not an object")
            name = raw_model.get("name") or raw_model.get("model")
            size = raw_model.get("size", 0)
            digest = raw_model.get("digest", "")
            details = raw_model.get("details") or {}
            if not isinstance(name, str) or not name:
                raise OllamaProtocolError(f"model at position {position} has no name")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise OllamaProtocolError(f"model {name} has an invalid size")
            if not isinstance(digest, str) or not isinstance(details, dict):
                raise OllamaProtocolError(f"model {name} has invalid metadata")
            models.append(
                OllamaModel(
                    name=name,
                    size=size,
                    digest=digest,
                    parameter_size=str(details.get("parameter_size", "")),
                    quantization=str(details.get("quantization_level", "")),
                )
            )
        return models

    def embed(self, model: str, inputs: str | Sequence[str]) -> List[List[float]]:
        self.policy.validate_model(model)
        normalized_inputs = _normalize_inputs(inputs)
        response = self._request_json(
            "POST", "/api/embed", {"model": model, "input": normalized_inputs}
        )
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(normalized_inputs):
            raise OllamaProtocolError("embedding count does not match input count")
        validated: List[List[float]] = []
        dimensions: Optional[int] = None
        for position, vector in enumerate(embeddings):
            if not isinstance(vector, list) or not vector:
                raise OllamaProtocolError(f"embedding {position} is not a non-empty array")
            if not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in vector
            ):
                raise OllamaProtocolError(f"embedding {position} contains a non-finite number")
            if dimensions is None:
                dimensions = len(vector)
            elif len(vector) != dimensions:
                raise OllamaProtocolError("embedding dimensions are inconsistent")
            validated.append([float(value) for value in vector])
        return validated

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, str]],
        *,
        response_format: Optional[Mapping[str, Any] | str] = None,
    ) -> str:
        self.policy.validate_model(model)
        if not messages:
            raise OllamaProtocolError("chat requires at least one message")
        normalized_messages: List[Dict[str, str]] = []
        for position, message in enumerate(messages):
            if not isinstance(message, Mapping):
                raise OllamaProtocolError(f"chat message {position} is not an object")
            role = message.get("role")
            content = message.get("content")
            if role not in ("system", "user", "assistant") or not isinstance(content, str):
                raise OllamaProtocolError(f"chat message {position} has invalid role or content")
            normalized_messages.append({"role": role, "content": content})
        body: Dict[str, Any] = {
            "model": model,
            "messages": normalized_messages,
            "stream": False,
        }
        if response_format is not None:
            body["format"] = response_format
        response = self._request_json("POST", "/api/chat", body)
        response_message = response.get("message")
        if not isinstance(response_message, dict) or not isinstance(
            response_message.get("content"), str
        ):
            raise OllamaProtocolError("chat response has no message content")
        return response_message["content"]

    def _request_json(
        self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            try:
                data = json.dumps(payload, allow_nan=False).encode("utf-8")
            except (TypeError, ValueError) as ex:
                raise OllamaProtocolError(f"request is not valid JSON data: {ex}") from ex
            headers["Content-Type"] = "application/json"
        request = Request(self.endpoint + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_response = response.read()
        except HTTPError as ex:
            try:
                detail = _http_error_detail(ex)
            finally:
                ex.close()
            raise OllamaAPIError(f"Ollama returned HTTP {ex.code}: {detail}") from ex
        except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as ex:
            reason = getattr(ex, "reason", ex)
            raise OllamaConnectionError(
                f"could not reach Ollama at {self.endpoint}: {reason}"
            ) from ex
        try:
            decoded = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as ex:
            raise OllamaProtocolError("Ollama returned invalid JSON") from ex
        if not isinstance(decoded, dict):
            raise OllamaProtocolError("Ollama response is not a JSON object")
        if isinstance(decoded.get("error"), str):
            raise OllamaAPIError(decoded["error"])
        return decoded


def _normalize_inputs(inputs: str | Sequence[str]) -> List[str]:
    if isinstance(inputs, str):
        normalized = [inputs]
    elif isinstance(inputs, Sequence):
        normalized = list(inputs)
    else:
        raise OllamaProtocolError("embedding input must be text or a sequence of text")
    if not normalized or not all(isinstance(value, str) and value for value in normalized):
        raise OllamaProtocolError("embedding inputs must be non-empty strings")
    return normalized


def _http_error_detail(error: HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
        if isinstance(body, dict) and isinstance(body.get("error"), str):
            return body["error"]
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        pass
    return error.reason or "request failed"
