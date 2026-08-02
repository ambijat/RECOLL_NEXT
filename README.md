# Recoll Next

A local-first knowledge system built on the inherited Recoll indexing engine. Recoll
remains the authority for extraction, metadata, document identity, and lexical search;
Recoll Next adds local semantic retrieval, cited Ollama answers, Perspective Memory,
and tamper-evident event history.

The Python/Tk product slice and its JSON API are implemented and tested. The native
Qt dock is implemented in source but still needs a matching Qt/C++ SDK, a successful
build, and packaging validation before a binary release can be claimed.

Start every work session with [SESSION_START.md](SESSION_START.md).

New here? Read the [brochure](docs/BROCHURE.html) for what this is, or jump straight to
the [quick start guide](docs/QUICKSTART.html).

## Privacy and operating boundary

- Original documents and the Recoll/Xapian index remain authoritative.
- Ollama is loopback-only by default; cloud models and remote content processing are
  outside the supported policy.
- Semantic SQLite stores, prompts, answers, runtime ledgers, and exported knowledge
  remain local and are excluded from Git by default.
- Exact Recoll search continues when Ollama or the semantic sidecar is unavailable.
- Generated answers are rejected unless their citations resolve to supplied evidence.

## Quick start

Requirements for the validated Windows path are Python, an installed Recoll runtime,
and local Ollama with the configured models. Environment creation itself is offline
and dependency-free:

```powershell
python src\semantic\initsemenv.py .venv --verify
.\.venv\Scripts\Activate.ps1
python src\semantic\recoll_ai.py doctor
python -W error::ResourceWarning -m unittest discover -s tests\semantic
```

Launch the everyday evidence workspace with `AI-Perspective.bat`, or run:

```powershell
python src\semantic\recoll_ai_gui.py --store .local\semantic.sqlite3
```

Semantic indexing is an explicit maintenance operation. Read the
[Quick Start Guide](docs/QUICKSTART.html) and
[Operations Runbook](docs/OPERATIONS_RUNBOOK.md) before using
`Rebuild-Index.bat` or `recoll_ai.py sync`, especially when working with a partial
Recoll query.

## Foundation retained

- Document extraction, metadata, lexical indexing, and search engine source.
- Qt application and Python binding source needed for the rebuild.
- Component licenses, copyright notices, and provenance required by the inherited GPL
  code.
- Tested local semantic search and the hash-chained event ledger.

## New product documents

- [Documentation map](docs/README.md)
- [Portability contract](docs/PORTABILITY_CONTRACT.md)
- [Mandatory agent handoff](docs/AGENT_HANDOFF.md)
- [Verified workstation baseline](docs/WORKSTATION_BASELINE.md)
- [Development and build](docs/DEVELOPMENT_AND_BUILD.md)
- [Configuration reference](docs/CONFIGURATION_REFERENCE.md)
- [Local CLI and JSON API](docs/API_CONTRACT.md)
- [Data migration](docs/DATA_MIGRATION.md)
- [Transfer manifest template](docs/TRANSFER_MANIFEST_TEMPLATE.md)
- [Operations runbook](docs/OPERATIONS_RUNBOOK.md)
- [Component catalog](docs/COMPONENT_CATALOG.md)
- [Security and privacy](docs/SECURITY_AND_PRIVACY.md)
- [Provenance and licensing](docs/PROVENANCE_AND_LICENSING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Prismatic Search Charter](docs/PRISMATIC_SEARCH.md)
- [Xapian-first hybrid search protocol](docs/XAPIAN_FIRST_PROTOCOL.md)
- [Goal Fidelity Covenant](docs/GOAL_FIDELITY.md)
- [Local AI runtime](docs/LOCAL_AI_RUNTIME.md)
- [Semantic index foundation](docs/SEMANTIC_INDEX.md)
- [Semantic retrieval](docs/SEMANTIC_RETRIEVAL.md)
- [Local cited answers](docs/CITED_ANSWERS.md)
- [Perspective Memory](docs/PERSPECTIVE_MEMORY.md)
- [AI Perspective workspace](docs/AI_WORKSPACE.md)
- [Event ledger](docs/EVENT_LEDGER.md)
- [Project governance ledger](governance/README.md)
- [Roadmap](docs/ROADMAP.md)

Historical upstream Git metadata is lineage only. Remote access is denied by default;
publication is limited to an exact destination and operation explicitly authorized by
the user after the local acceptance gate.

## Project status and participation

The [roadmap](docs/ROADMAP.md) and [session briefing](SESSION_START.md) distinguish
implemented, live-validated, and planned work. Known release gaps include the native
Qt build/package, a second-physical-machine portability proof, full-corpus relevance
measurement, and eventual vector-search acceleration.

Before contributing, read [CONTRIBUTING.md](CONTRIBUTING.md). Security and privacy
reports follow [SECURITY.md](SECURITY.md). Source distribution readiness is governed
by [docs/PUBLICATION_CHECKLIST.md](docs/PUBLICATION_CHECKLIST.md). See
[CHANGELOG.md](CHANGELOG.md) for the unreleased feature summary.

## License and provenance

Recoll Next is distributed under the GNU General Public License, version 2 or (at your
option) any later version, except for retained components that carry their own
compatible notices. See [LICENSE.md](LICENSE.md), [src/COPYING](src/COPYING), and the
[provenance guide](docs/PROVENANCE_AND_LICENSING.md). Model artifacts and user corpus
content are separate works and are not distributed by this repository.
