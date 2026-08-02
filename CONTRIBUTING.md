# Contributing to Recoll Next

Recoll Next welcomes focused improvements that preserve its local-first,
evidence-bearing design. This repository is independent from upstream Recoll; the
inherited remote is lineage metadata. Remote access is denied unless the user names
the exact destination and requested publication operation.

## Before changing the repository

1. Read `AGENTS.md`, `SESSION_START.md`, and every document in the session briefing's
   **Required reading** list.
2. Verify `git status --short` and preserve unrelated work.
3. Verify `governance/events.jsonl` before adding a governed decision or milestone.
4. Check the proposal against `docs/GOAL_FIDELITY.md` and the relevant normative
   contract.

Do not commit corpus files, semantic databases, prompts, generated answers, runtime
ledgers, credentials, local profiles, model blobs, virtual environments, or build
outputs. Keep Ollama on loopback unless an explicit governed policy change says
otherwise.

## Change expectations

- Keep Recoll/Xapian authoritative for documents, metadata, identity, and lexical
  search.
- Keep semantic data disposable and model/segmenter-versioned.
- Preserve Exact search when AI services fail.
- Carry evidence identifiers through retrieval, generation, validation, and UI.
- Add focused tests for behavior changes and update every affected contract or
  runbook.
- Append major goals, architectural decisions, and completed milestones through the
  event-ledger implementation; never edit historical JSONL lines.
- Do not weaken a fiduciary, privacy, citation, or portability invariant without the
  documented change-control process.

## Verification

From the repository root:

```powershell
python -m compileall -q src\semantic
python -W error::ResourceWarning -m unittest discover -s tests\semantic
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
git diff --check
git status --short
```

Native C++/Qt changes also require a compatible out-of-tree build and an exercised AI
Perspective workflow before claiming binary validation. If the required toolchain or
local runtime is unavailable, document the skipped check precisely.

## Commit and review hygiene

Use small local commits with intentional messages. A change is ready for review when
tests pass, documentation matches behavior, the current ledger head appears in
`governance/CHECKPOINTS.md`, and remaining local files are explicitly attributed.
Never fetch, pull, push, or open a pull request unless the exact action and destination
are explicitly authorized. A publication authorization does not permit force-push,
remote ref deletion, unrelated refs, private artifacts, or a different remote.

By contributing, you agree that your contribution is licensed under the project terms
described in `LICENSE.md`, while preserving any more specific notice on retained
third-party code.
