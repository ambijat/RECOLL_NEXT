# Local AI runtime

## First executable artifact

`recoll_ai.py` is the command-line entry point for the new semantic subsystem. Its
first command verifies that a policy-compliant local Ollama service is ready before
Recoll, the vector store, or the Qt interface attempts to use it.

From the repository root:

```text
python src/semantic/recoll_ai.py doctor
```

For automation:

```text
python src/semantic/recoll_ai.py doctor --json
```

Default requirements:

- endpoint: `http://127.0.0.1:11434`;
- embedding model: `embeddinggemma`;
- chat model: `gemma3:4b`.

Overrides remain local-only:

```text
python src/semantic/recoll_ai.py doctor \
  --endpoint http://localhost:11434 \
  --embedding-model embeddinggemma \
  --chat-model gemma3:1b
```

## Status and exit contract

| Exit | Status | Meaning |
|---:|---|---|
| `0` | `ready` | Ollama is reachable and both required models are installed. |
| `1` | `unavailable` or `error` | The service is stopped, unreachable, or returned an invalid response. |
| `2` | `models_missing` | Ollama is running but one or more required models must be pulled. |
| `3` | `policy_error` | The endpoint or model violates local-only policy. |

The diagnostic never downloads, starts, or changes Ollama. It only performs a local
readiness check and reports the next action.

## Enforced policy

The adapter accepts only explicit HTTP loopback endpoints:

- `127.0.0.0/8`;
- `[::1]`;
- `localhost`.

It rejects HTTPS/cloud endpoints, LAN addresses, arbitrary hostnames, URL credentials,
paths, queries, fragments, and cloud-model names. Hostnames are not resolved during
policy checks because DNS would enlarge the trust boundary.

## Adapter contract

`rclsem_ollama.py` uses only the Python standard library and exposes:

- `list_models()` for readiness and model selection;
- `embed()` for validated batch embeddings;
- `chat()` for non-streaming generation and structured response schemas.

Responses are checked for valid JSON, expected shapes, finite embedding values,
consistent vector dimensions, and matching batch sizes. Typed errors distinguish
policy, connection, API, and protocol failures.

This dependency-free boundary will replace direct calls to the external `ollama`
Python package in the inherited semantic prototype.
