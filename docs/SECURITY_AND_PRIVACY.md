# Security and privacy model

## Protected assets

- original corpus files and filenames;
- Recoll extracted text, metadata, paths, and query history;
- semantic segments and embeddings;
- user questions, prompts, generated answers, and Perspective Memory;
- model files and local runtime configuration;
- project source/history and governance evidence;
- credentials or secrets that may exist elsewhere in the host environment.

## Trust boundaries

| Boundary | Default trust |
| --- | --- |
| Original files to installed Recoll extractors | Local, but parsers process untrusted document formats |
| Recoll/Xapian to semantic bridge | Local authoritative read boundary |
| Project Python to Ollama loopback HTTP | Local model boundary, policy validated |
| CLI to GUI child process | Local argument-vector/JSON boundary |
| Semantic components to SQLite | Private derived-data boundary |
| Components to runtime ledger | Minimized audit boundary |
| Repository to Git remote | Prohibited |
| Local model to non-loopback endpoint | Prohibited without governed policy change |

Loopback reduces network exposure but is not an authentication mechanism. Other local
processes under the same host/user boundary may access listening services or files.

## Security invariants

- Exact Recoll search never depends on model availability.
- Only loopback Ollama endpoints pass the default adapter policy.
- Cloud model identifiers are rejected by default.
- Generated answers must cite supplied primary segments or explicitly decline.
- Perspective Memory is secondary and gated by current source revisions.
- Logs and ledgers do not contain full documents, private prompts, credentials, or
  unrestricted exception state.
- The command boundary reports typed failures without tracebacks that could expose
  extracted text.
- Runtime stores are Git-ignored and remain local unless deliberately migrated.
- Hash-chain verification precedes governance milestones.

## Threats and controls

| Threat | Current control | Residual risk |
| --- | --- | --- |
| Accidental cloud disclosure | Loopback endpoint and cloud-model policy | Future code/config could weaken policy; regression tests required |
| Prompt injection inside documents | System prompt limits model to supplied evidence and validates IDs | Model can still produce misleading synthesis supported by broad evidence; user inspection required |
| Invented citations | Exact segment-ID allowlist | A valid ID does not prove every clause is faithfully entailed |
| Stale AI memory | Document/revision citation revalidation | Semantic store itself may lag Recoll until synchronized |
| Corrupt vectors/schema | Dimension/version checks and rebuildability | SQLite corruption requires restore/rebuild tooling |
| Ledger tampering | Hash chain, fsync, checkpointed heads | Whole-chain/checkpoint replacement remains possible without external signature |
| Malicious document parser input | Existing Recoll extraction isolation/process design | Inherited parser/tool vulnerabilities remain a platform maintenance concern |
| Shell injection | GUI uses argument vectors; CLI validates structure | Operators can still construct unsafe shell wrappers externally |
| Local file disclosure | `.local` ignored; no content in project ledger | Host ACLs/encryption/backup policy are operator responsibilities |
| Denial of service | Timeouts, bounded evidence, cancellation | Large sync/full vector scan and generation remain resource intensive |

## Sensitive data locations

| Location | Potential sensitive content |
| --- | --- |
| Original corpus roots | Full documents and filenames |
| Recoll `dbdir` | Searchable terms, positions, stored data/metadata |
| Recoll profile/history/cache | Paths, queries, extracted/cache state |
| Semantic SQLite store | Segments, paths, hashes, embeddings, questions, answers |
| Runtime JSONL ledger | Document/segment/perspective identifiers and metrics |
| Exported Markdown answers | Generated interpretations and cited source paths |
| Process command lines | User query text passed as an argument |

The current GUI/CLI passes the query as a child-process argument, so it may be visible
to same-host process inspection. A future private IPC request body would reduce that
exposure.

## Operational hardening

- Use operating-system account isolation, disk encryption, and private ACLs for
  corpus, Recoll profile, Xapian, `.local`, exports, and backups.
- Bind Ollama to loopback and avoid firewall exposure.
- Keep Recoll, extractors, Ollama, Python, Qt, and the operating system patched under
  an operator-approved offline/update process.
- Treat document formats as untrusted input and minimize unnecessary external
  extractors.
- Stop writers before backups and verify restored data before deleting rollback.
- Store corpus hash manifests with private media when filenames are sensitive.
- Use `--no-remember` for ephemeral questions and securely manage exported answers.

## Incident response

If private content may have crossed a prohibited boundary:

1. stop the affected process without deleting evidence;
2. disconnect the unauthorized endpoint or network path;
3. preserve bounded logs, configuration, commit, and ledger heads;
4. do not put leaked content into a governance event;
5. identify affected stores, prompts, models, and destinations;
6. rotate any exposed credentials outside the repository;
7. restore local-only configuration and add a regression test;
8. document the architectural cause and corrective decision in privacy-safe terms.

If a ledger fails verification, preserve it byte-for-byte and follow the recovery
rules in `EVENT_LEDGER.md`; never “fix” historical lines.

## Known security work

- signed/external ledger checkpoints;
- user-visible Perspective Memory inspect/delete/retention controls;
- encrypted-at-rest profile option;
- private IPC that avoids query text in process arguments;
- packaged ACL defaults;
- threat testing of hybrid retrieval and document prompt injection;
- dependency inventory/SBOM for a reproducible native package.

