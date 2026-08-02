# Security policy

## Supported state

The current supported security boundary is the latest local `master` checkpoint. The
Python/Tk slice is tested; the native Qt dock is not yet distributed as a validated
binary. This project does not promise security fixes for older local checkpoints.

## Reporting a vulnerability

Do not place private corpus content, credentials, exploit payloads containing private
data, or unrestricted environment dumps in a public issue. Until a dedicated private
reporting channel is established on the eventual hosting service, prepare a minimal
local report containing:

- affected commit and component;
- security invariant or trust boundary involved;
- bounded reproduction steps using synthetic data;
- observed versus expected behavior; and
- whether content may have crossed loopback, process, filesystem, or Git boundaries.

If private content may have crossed a prohibited boundary, follow the incident steps
in `docs/SECURITY_AND_PRIVACY.md` first. Preserve evidence, disconnect the unauthorized
path, and rotate exposed credentials outside this repository.

## Security invariants

- Ollama endpoints are loopback-only by default.
- Exact lexical search does not depend on AI availability.
- Generated citations must resolve to supplied primary evidence.
- Runtime stores and private operational evidence are not committed.
- Errors, logs, and ledgers exclude full document bodies, prompts, credentials, and
  unrestricted exception state.
- The governance chain is verified before and after governed milestones.

The full threat model, residual risks, and response procedure are in
`docs/SECURITY_AND_PRIVACY.md`.
