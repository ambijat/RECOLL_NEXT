# Source publication checklist

## Purpose

This checklist prepares a source checkpoint for a public Git host without weakening
Recoll Next's local-first or provenance rules. It does not itself authorize a network
or Git remote action. Publication requires the user to name the exact destination and
operation after the local checkpoint passes.

## Publication scope

Include tracked source, tests, public documentation, legal notices, and the verified
project governance chain. Exclude:

- corpus documents and private filename inventories;
- Recoll profiles, Xapian databases, semantic SQLite stores, and runtime ledgers;
- prompts, generated answers, exports, logs, crash dumps, and environment dumps;
- Ollama executables/model blobs, Python environments, build outputs, and IDE state;
- private transfer manifests, audit capsules, credentials, keys, and tokens.

The historical Recoll remote is lineage metadata. An authorized publication uses a
separate, exact destination and may push only the selected product branch/ref. It does
not authorize fetch, pull, force-push, remote deletion, unrelated refs, private
artifacts, or access to another remote.

## Local acceptance gate

1. Confirm the intended branch and inspect all tracked, untracked, and ignored files.
2. Confirm `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE.md`, the documentation
   map, and current session/restart briefings agree with implemented behavior.
3. Check all local documentation links and scan tracked files for accidental secrets,
   private paths, databases, archives, generated artifacts, and oversized files.
4. Run:

   ```powershell
   python -m compileall -q src\semantic
   python -W error::ResourceWarning -m unittest discover -s tests\semantic
   python src\semantic\rclsem_ledger.py verify governance\events.jsonl
   git diff --check
   git status --short
   ```

5. Record any unavailable native build or live runtime checks as limitations; never
   convert a skipped check into a passing claim.
6. Append the publication-readiness decision/milestone through the ledger, add the
   resulting head to `governance/CHECKPOINTS.md`, verify again, and create an
   intentional local commit.
7. Re-run the acceptance gate from the committed tree. The tree must be clean except
   for files deliberately excluded and explicitly named in the handoff.

## Host handoff

Before an operator creates the public repository, review the host's visibility,
default branch, issue/security-reporting settings, license display, and whether any
automation would upload artifacts or contact external services. Push only the selected
local product branch. Do not publish tool-owned refs, private bundles, ignored runtime
data, or unrelated historical remote-tracking refs.

After the first authorized push, independently inspect the hosted file list and clone
the public branch into a new directory. Re-run link checks, ledger verification, and
the dependency-free semantic suite there before announcing availability.
