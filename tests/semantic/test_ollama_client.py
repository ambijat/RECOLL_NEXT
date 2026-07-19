import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai import doctor_report  # noqa: E402
from rclsem_ollama import (  # noqa: E402
    OllamaAPIError,
    OllamaClient,
    OllamaPolicy,
    OllamaPolicyError,
    OllamaProtocolError,
)


class FakeOllamaHandler(BaseHTTPRequestHandler):
    models = [
        {
            "name": "embeddinggemma:latest",
            "size": 622_000_000,
            "digest": "embed-digest",
            "details": {
                "parameter_size": "300M",
                "quantization_level": "F16",
            },
        },
        {
            "name": "gemma3:4b",
            "size": 3_300_000_000,
            "digest": "chat-digest",
            "details": {
                "parameter_size": "4.3B",
                "quantization_level": "Q4_K_M",
            },
        },
    ]
    last_request = None

    def do_GET(self):
        if self.path == "/api/tags":
            self._send(200, {"models": self.models})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).last_request = {"path": self.path, "body": request}
        if self.path == "/api/embed":
            inputs = request["input"]
            self._send(
                200,
                {
                    "model": request["model"],
                    "embeddings": [[float(i), 0.5] for i, _ in enumerate(inputs, start=1)],
                },
            )
        elif self.path == "/api/chat":
            self._send(
                200,
                {
                    "model": request["model"],
                    "message": {"role": "assistant", "content": '{"answer":"local"}'},
                    "done": True,
                },
            )
        elif self.path == "/api/fail":
            self._send(500, {"error": "model failed"})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, format, *args):
        pass

    def _send(self, status, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class FakeOllamaServer:
    def __enter__(self):
        FakeOllamaHandler.models = list(FakeOllamaHandler.models)
        FakeOllamaHandler.last_request = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.endpoint = f"http://{host}:{port}"
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class OllamaPolicyTest(unittest.TestCase):
    def test_accepts_only_explicit_loopback_endpoints(self):
        policy = OllamaPolicy()
        self.assertEqual(
            "http://127.0.0.1:11434",
            policy.validate_endpoint("http://127.0.0.1:11434/"),
        )
        self.assertEqual(
            "http://localhost:11434",
            policy.validate_endpoint("http://localhost:11434"),
        )
        self.assertEqual(
            "http://[::1]:11434", policy.validate_endpoint("http://[::1]:11434")
        )
        for endpoint in (
            "https://localhost:11434",
            "http://ollama.example:11434",
            "http://192.168.1.10:11434",
            "http://localhost:11434/api",
            "http://user:pass@localhost:11434",
            "http://localhost:not-a-port",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(OllamaPolicyError):
                    policy.validate_endpoint(endpoint)

    def test_rejects_cloud_models(self):
        policy = OllamaPolicy()
        for model in ("gpt-oss:120b-cloud", "model:cloud", "model-cloud:latest"):
            with self.subTest(model=model):
                with self.assertRaises(OllamaPolicyError):
                    policy.validate_model(model)
        policy.validate_model("gemma3:4b")


class OllamaClientTest(unittest.TestCase):
    def test_lists_models(self):
        with FakeOllamaServer() as fake:
            models = OllamaClient(fake.endpoint).list_models()
        self.assertEqual(["embeddinggemma:latest", "gemma3:4b"], [m.name for m in models])
        self.assertEqual("Q4_K_M", models[1].quantization)

    def test_batches_embeddings_and_validates_dimensions(self):
        with FakeOllamaServer() as fake:
            embeddings = OllamaClient(fake.endpoint).embed(
                "embeddinggemma", ["first", "second"]
            )
            request = FakeOllamaHandler.last_request
        self.assertEqual([[1.0, 0.5], [2.0, 0.5]], embeddings)
        self.assertEqual("/api/embed", request["path"])
        self.assertEqual(["first", "second"], request["body"]["input"])

    def test_chat_is_non_streaming_and_forwards_schema(self):
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        with FakeOllamaServer() as fake:
            content = OllamaClient(fake.endpoint).chat(
                "gemma3:4b",
                [{"role": "user", "content": "Use only evidence"}],
                response_format=schema,
            )
            request = FakeOllamaHandler.last_request
        self.assertEqual('{"answer":"local"}', content)
        self.assertFalse(request["body"]["stream"])
        self.assertEqual(schema, request["body"]["format"])

    def test_rejects_malformed_embedding_response(self):
        with FakeOllamaServer() as fake:
            client = OllamaClient(fake.endpoint)
            original = client._request_json
            client._request_json = lambda *args, **kwargs: {"embeddings": [[1.0], [1.0, 2.0]]}
            with self.assertRaisesRegex(OllamaProtocolError, "dimensions"):
                client.embed("embeddinggemma", ["one", "two"])
            client._request_json = original

    def test_surfaces_api_error_detail(self):
        with FakeOllamaServer() as fake:
            client = OllamaClient(fake.endpoint)
            with self.assertRaisesRegex(OllamaAPIError, "model failed"):
                client._request_json("POST", "/api/fail", {})


class DoctorTest(unittest.TestCase):
    def test_ready_when_required_local_models_are_installed(self):
        with FakeOllamaServer() as fake:
            code, report = doctor_report(
                endpoint=fake.endpoint,
                embedding_model="embeddinggemma",
                chat_model="gemma3:4b",
                timeout=1,
            )
        self.assertEqual(0, code)
        self.assertEqual("ready", report["status"])
        self.assertEqual([], report["missing_models"])

    def test_reports_missing_models_with_pull_instruction(self):
        with FakeOllamaServer() as fake:
            code, report = doctor_report(
                endpoint=fake.endpoint,
                embedding_model="embeddinggemma",
                chat_model="missing:1b",
                timeout=1,
            )
        self.assertEqual(2, code)
        self.assertEqual(["missing:1b"], report["missing_models"])
        self.assertIn("ollama pull missing:1b", report["next_action"])

    def test_policy_error_is_reported_without_network_access(self):
        code, report = doctor_report(
            endpoint="https://ollama.example:443",
            embedding_model="embeddinggemma",
            chat_model="gemma3:4b",
            timeout=1,
        )
        self.assertEqual(3, code)
        self.assertEqual("policy_error", report["status"])


if __name__ == "__main__":
    unittest.main()
