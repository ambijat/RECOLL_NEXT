# Local cited answers

## Customer deliverable

`recoll_ai.py ask` turns retrieved local evidence into an answer or selected
perspective using `gemma3:4b`. It is the first complete customer-output contract for
the future Qt **Ask AI** button.

The semantic store must contain synchronized documents before an answer can be
grounded. An empty store returns an explicit insufficient-evidence response without
calling the chat model.

```powershell
python src\semantic\recoll_ai.py ask `
  --store .local\semantic.sqlite3 `
  "What decisions have we made about local AI and why?"
```

Available views are `answer`, `summary`, `timeline`, `contradictions`, `decisions`,
and `actions`. For example:

```powershell
python src\semantic\recoll_ai.py ask `
  --store .local\semantic.sqlite3 `
  --view decisions `
  "What decisions have we made about local AI and why?"
```

Use `--json` for the stable machine-readable structure that the GUI will consume.

## Evidence boundary

The answer composer:

1. Retrieves a bounded number of semantic evidence segments.
2. Sends only those segments and the local question to loopback Ollama.
3. Requires structured JSON containing an answer, an insufficient-evidence flag, and
   exact cited segment IDs.
4. Constrains the structured-output citation field to an enum of the exact supplied
   segment IDs, reducing model copy errors without permitting any new identifier.
5. Independently rejects malformed JSON, unknown segment IDs, and supported answers without a
   citation.
6. Resolves accepted citations back to document identity, revision, path, source
   offsets, text, and retrieval score for presentation.

Generated prose is never stored as indexed fact. Original files and the Recoll index
remain authoritative.

## Audit events

The composer records `answer.local.started`, `answer.local.completed`, or
`answer.local.failed`. Events contain the SHA-256 question digest, model, requested
view, counts, citation segment IDs, evidence status, and typed failure only. Questions,
prompts, evidence bodies, answers, paths, and exception messages do not enter the
ledger.

Semantic search emits its own `search.semantic.*` events in the same command session.

## Validation

The semantic suite covers citation resolution, structured-output citation allowlists,
invented citation rejection, mandatory citations, invalid model JSON, empty-store
decline, question privacy, and command/view parsing.

A live run embedded two synthetic project decisions with `embeddinggemma`, retrieved
them for a local-AI question, and generated a supported `gemma3:4b` answer citing the
supplied segment. The first generation took about 107 seconds, establishing the need
for asynchronous progress and cancellation in the Qt interface.

A later live regression of the academic-PDF `contradictions` view reproduced an
unknown-citation rejection under the former generic-string schema. Constraining that
schema to the two supplied segment IDs produced a supported answer with two validated
citations in 179 seconds. The validator remains mandatory even when constrained
generation succeeds.

## GUI boundary

The Qt **Ask AI** action should execute this contract asynchronously, display the
answer separately from source facts, render every citation as a navigable evidence
card, and preserve ordinary Recoll search while generation is running or unavailable.
