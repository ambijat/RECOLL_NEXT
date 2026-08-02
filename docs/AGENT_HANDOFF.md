# Mandatory AI-agent handoff protocol

## Purpose

This protocol preserves project intent, evidence, privacy, and executable continuity
when one AI agent hands work to another. Chat history is convenience context, not the
project source of truth. Durable handoff lives in tracked Markdown, code, tests, Git
commits, and the verified project ledger.

Every agent must follow this protocol before making changes.

## Instruction priority

An agent obeys active system/developer instructions first, then the nearest applicable
repository `AGENTS.md`, then the user's current request, then project documentation.
If an instruction conflicts with the local-first/default-deny remote covenant or
requests a materially broader action than the user authorized, stop and report the
conflict.

Project documentation does not authorize destructive actions, remote access, model
downloads, publication, or copying private data merely because it describes how such
an operator-approved action could be performed.

## Mandatory read order

Before any repository mutation, every agent must read completely:

1. `AGENTS.md`;
2. `SESSION_START.md`;
3. `docs/PORTABILITY_CONTRACT.md`;
4. this `docs/AGENT_HANDOFF.md`;
5. `docs/GOAL_FIDELITY.md`;
6. the architecture/protocol/runbook documents relevant to the requested subsystem.

Read-only orientation may occur before the full list is complete. No edit, generated
file, dependency installation, runtime-store mutation, commit, or external action may
occur until mandatory orientation is complete.

## Session entry audit

The receiving agent must establish facts rather than assuming the previous message
is current:

```powershell
git status --short
git log -5 --oneline
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
```

Then inspect:

- the current milestone and known defects in `SESSION_START.md`;
- working-tree changes and their likely owner;
- recent commits and checkpoint rows;
- the exact requested scope;
- availability of local Recoll, Ollama, Python, and data stores only when relevant.

Never discard, reset, overwrite, reformat, or absorb unrelated user changes. If a
dirty file overlaps the requested edit, inspect the diff and work around it or ask for
direction.

## Inherited facts versus verified facts

Classify handoff information as:

- **Tracked fact** — supported by current code/docs/commit.
- **Verified runtime fact** — observed locally during this session.
- **Historical report** — claimed by a prior agent/user but not rechecked.
- **Plan** — intended work not yet implemented.
- **Known limitation** — deliberately incomplete or unvalidated behavior.

Do not convert a plan or historical report into “implemented” language. Correct stale
documentation when local evidence contradicts it; for example, runtime versions must
come from the selected machine, not memory.

## Change workflow

1. Restate the intended outcome and identify the governing contract.
2. Inspect relevant source, tests, and existing documentation.
3. Preserve the Xapian-first, local-only, evidence-bearing boundaries.
4. Make the smallest coherent implementation.
5. Add or update tests proportional to risk.
6. Run focused checks, then the complete semantic suite for a milestone.
7. Update feature docs, configuration/operations docs, and `SESSION_START.md` when
   their facts changed.
8. Append major decisions through the ledger implementation; never edit an old event.
9. Verify the complete chain and add its head to `governance/CHECKPOINTS.md`.
10. Commit locally with an intentional message.
11. Confirm the final working tree and report uncompleted work honestly.

No step contacts a Git remote unless the user has explicitly named both the exact
destination and operation and the publication acceptance gate has passed. That narrow
authorization does not extend to fetch, pull, force-push, ref deletion, private
artifacts, or another remote.

## Ledger discipline

Project decisions and milestones belong in `governance/events.jsonl`. High-volume
runtime activity belongs beside the selected semantic store. Never commit a runtime
ledger merely because it exists under the workspace.

Allowed project payloads contain bounded decisions, document names, test counts, and
commit hashes. They exclude original document bodies, prompts, credentials, private
corpus inventories, environment dumps, and unrestricted errors.

Always append through `EventLedger` or its CLI and verify afterward:

```powershell
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
```

If verification fails, preserve the chain and stop ledger mutation.

## Runtime and external-action boundary

Agents may perform relevant local read-only diagnostics. A request to develop or test
the project does not automatically authorize:

- Git fetch/pull/push or opening pull requests, except for the exact destination and
  operation explicitly authorized under the publication policy;
- model pulls or package downloads;
- cloud inference or non-loopback endpoints;
- deleting/rebuilding a user's only Xapian or semantic database;
- moving or copying private corpus data outside the named scope;
- killing unrelated desktop processes;
- publishing generated answers or documentation externally.

Use temporary or dedicated sample stores for destructive/rebuild tests.

## Required handoff record

Before ending a material implementation session, make the repository self-explanatory
and report this compact record to the next operator/agent:

```text
Outcome achieved
Local commits created
Files/contracts materially changed
Tests and live validations run, with exact outcomes
Project ledger event count and head hash
Runtime stores touched but not committed
Working-tree status and ownership of remaining changes
Known limitations and the next bounded artifact
Any action requiring new user authority
```

If current state, milestone, architecture, operating rules, or risks changed, encode
them in `SESSION_START.md`; do not rely on the final chat response.

## Cross-agent prompt template

An operator can hand the project to another agent with:

```text
Work only in this local Recoll Next repository. Treat Git remote access as denied
unless the user explicitly names the exact destination and operation; never contact a
non-local model endpoint. Read AGENTS.md, SESSION_START.md,
docs/PORTABILITY_CONTRACT.md, and docs/AGENT_HANDOFF.md completely before changing
anything. Verify git status and governance/events.jsonl. Treat Xapian as authoritative
and SQLite/Ollama outputs as derived. Preserve unrelated changes. Continue from the
current milestone, test the result, update durable Markdown and the ledger, and commit
locally only.
```

The prompt supplements but never replaces the tracked contracts.

## Completion gate

An agent must not report a milestone complete unless:

- requested behavior exists rather than only being planned;
- relevant tests pass or failures are precisely documented;
- live validation is performed where the claim depends on local Recoll/Ollama;
- privacy and citation boundaries remain intact;
- portability/configuration docs reflect new files, flags, dependencies, or schemas;
- the governance chain verifies;
- commits are local only; and
- the working tree is clean or remaining files are explicitly attributed.
