# Hash-chained event ledger

## Purpose

The ledger provides a tamper-evident, ordered history of important local events. It
uses blockchain's useful primitive—a chain of cryptographic hashes—without tokens,
mining, peer-to-peer networking, or distributed consensus.

It can prove that the current file is internally consistent. It cannot prove that an
attacker did not replace the entire ledger and all external checkpoints. Later
milestones may periodically sign or export the head hash to separately controlled
storage.

## Storage format

The ledger is UTF-8 JSON Lines. Each line is one canonical event with these fields:

- `schema`: currently `recoll.event.v1`.
- `sequence`: monotonically increasing integer beginning at 1.
- `timestamp`: UTC ISO-8601 time.
- `event_type`: namespaced action such as `semantic.query.completed`.
- `actor`: component or user identity available to the application.
- `session_id`: identifier correlating events in one run or work session.
- `payload`: bounded JSON metadata.
- `previous_hash`: SHA-256 hash of the previous event, or 64 zeroes for genesis.
- `hash`: SHA-256 of the canonical event excluding the `hash` field.

The implementation flushes and calls `fsync` after every append and takes an
inter-process file lock during validation and append.

## Event taxonomy

Initial namespaces:

- `project.*`, `architecture.*`, `milestone.*`, `governance.*` — durable project
  mission, decision, milestone, and fiduciary-governance events.
- `session.*` — session start, checkpoint, and completion.
- `config.*` — configuration changes; store changed key names and value hashes for
  sensitive values, not secrets.
- `index.lexical.*` — Recoll indexing start, completion, failure, and document counts.
- `index.semantic.*` — embedding synchronization and collection rebuilds.
- `search.lexical.*`, `search.semantic.*`, `search.hybrid.*` — query lifecycle,
  latency, filters, result identifiers, and scores. Avoid raw query text by default;
  store a digest unless diagnostic consent is enabled.
- `model.embedding.*`, `model.generation.*` — model, duration, token/size metrics, and
  outcome. Never store full prompts or returned private passages.
- `answer.*` — answer lifecycle and cited segment identifiers.
- `ledger.*` — verification and checkpoint operations.
- `security.*` — policy decisions, rejected remote endpoints, and integrity failures.

## What must never be recorded

- Credentials, API keys, authentication cookies, or private keys.
- Full document bodies or extracted passages.
- Full prompts containing document content.
- Environment-variable dumps or unrestricted exception locals.
- Personal data unless it is essential, explicitly classified, and minimized.

## Verification and recovery

Run:

```text
python src/semantic/rclsem_ledger.py verify PATH_TO_LEDGER
```

Verification checks JSON validity, schema, sequence continuity, previous hashes, and
event hashes. Never silently repair a failed chain. Preserve the file, diagnose the
first invalid line, and create an explicit recovery ledger whose genesis event points
to the last independently trusted head hash.

## Concurrency and scope

One ledger file supports multiple local processes through a file lock. Keep each
product profile/configuration in its own ledger. High-volume diagnostic telemetry
should use ordinary rotating logs; only durable product/audit events belong here.

The versioned project-governance chain is `governance/events.jsonl`. Runtime product
profiles must use separate ledgers so private operational identifiers are never added
to repository history.
