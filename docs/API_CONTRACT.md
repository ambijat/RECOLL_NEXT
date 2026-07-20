# Local CLI and JSON API contract

## Boundary

`src/semantic/recoll_ai.py` is the shared automation boundary for the Tk companion,
native Qt dock, tests, scripts, and future packaging. It communicates through process
arguments, UTF-8 stdout JSON, stderr/human diagnostics, and exit status. It is not a
network server.

Pass `--json` for machine consumption. Consumers must inspect `status` and exit code,
must tolerate additional fields, and must not scrape the human-readable output.

## Common error envelope

Operational command failures return exit code `1` and:

```json
{
  "status": "error",
  "error_type": "TypedExceptionName",
  "error": "bounded diagnostic"
}
```

The CLI intentionally suppresses tracebacks because they may expose extracted text.
Callers show the typed error and bounded message without treating an error object as
an empty successful result.

`doctor` has its own status codes: `0` ready, `1` unavailable/general runtime error,
`2` required models missing, and `3` policy rejection.

## Doctor response

Representative ready shape:

```json
{
  "endpoint": "http://127.0.0.1:11434",
  "installed_models": [
    {
      "name": "embeddinggemma:latest",
      "parameter_size": "307.58M",
      "quantization": "BF16"
    }
  ],
  "local_only": true,
  "missing_models": [],
  "next_action": "Ollama is ready for local AI search.",
  "required_models": ["embeddinggemma", "gemma3:4b"],
  "status": "ready"
}
```

Non-ready states may include `unavailable`, `models_missing`, `policy_error`, or
`error`, with bounded `error` and `next_action` fields where applicable.

## Synchronization response

```json
{
  "status": "synchronized",
  "namespace_id": "sha256 namespace",
  "documents_added": 0,
  "documents_updated": 0,
  "documents_unchanged": 0,
  "documents_deleted": 0,
  "segments_embedded": 0
}
```

Counts describe one completed operation. Deletion occurs only after complete
enumeration when `--keep-missing` is absent.

## Semantic search response

```json
{
  "status": "ready",
  "result_count": 1,
  "results": [
    {
      "segment_id": "stable segment hash",
      "document_id": "Recoll rcludi",
      "source_revision": "source hash",
      "title": "Document title",
      "path": "file:///or/platform/path",
      "text": "bounded indexed segment",
      "source_start": 0,
      "source_end": 420,
      "similarity": 0.8123
    }
  ]
}
```

Current results are semantic-only. Exact and Prismatic hybrid modes described in the
Xapian-first protocol are planned coordinator/API additions, not current statuses.

## Cited answer response

```json
{
  "status": "answered",
  "answer": "Generated interpretation.",
  "insufficient_evidence": false,
  "view": "summary",
  "retrieved_count": 2,
  "citations": [
    {
      "segment_id": "allowed segment hash",
      "document_id": "Recoll rcludi",
      "source_revision": "source hash",
      "title": "Document title",
      "path": "source path",
      "text": "evidence segment",
      "source_start": 0,
      "source_end": 420,
      "similarity": 0.91
    }
  ],
  "remembered": true,
  "perspective_id": "content-addressed perspective hash"
}
```

When evidence is insufficient, citations may be empty and `remembered` remains
false. If storing secondary memory fails, the valid answer still succeeds with
`remembered: false` and `memory_error_type`; private exception details are not added.

The validator accepts only citation IDs present in the supplied evidence. A supported
answer without citations fails rather than returning this envelope.

## Perspective Memory response

```json
{
  "status": "memory_ready",
  "result_count": 1,
  "results": [
    {
      "perspective_id": "content hash",
      "question": "Prior local question",
      "answer": "Prior validated interpretation",
      "view": "decisions",
      "chat_model": "gemma3:4b",
      "embedding_model": "embeddinggemma",
      "created_at": "UTC ISO-8601",
      "citations": [
        {
          "segment_id": "segment hash",
          "document_id": "Recoll rcludi",
          "source_revision": "source hash"
        }
      ],
      "similarity": 0.95
    }
  ]
}
```

Only current citation triples are returned. A zero-result response is successful.

## Process and encoding requirements

- Invoke Python and script with an argument array, not shell-concatenated input.
- Decode stdout as UTF-8 and parse exactly one top-level JSON object.
- Treat non-zero exit as failure even if stdout exists.
- Do not place raw stdout/stderr into the project ledger.
- Allow cancellation by terminating only the owned child process.
- Search and generation have independent timeouts; UI cancellation remains available.
- Source open operations must use the returned path/URL through platform-safe APIs.

## Compatibility discipline

Adding a command, status, required field, enum value, or error semantic requires:

1. CLI parser and JSON implementation;
2. tests for human and JSON boundaries where applicable;
3. Tk and native Qt consumer review;
4. this API document and configuration reference update;
5. migration/compatibility note if an existing consumer could break.

Fields may be added compatibly. Removing or changing the meaning/type of an existing
field requires an explicit versioned contract rather than an undocumented edit.

## Perspective Memory instrumentation

`memory-search` emits `search.memory.started`, `search.memory.completed`, or
`search.memory.failed` through the selected runtime ledger. Payloads contain the
embedding model, limit, SHA-256 query digest, result count and perspective identifiers,
or a typed failure. They exclude the query, remembered question and answer text,
citations, paths, embeddings, and exception messages.
