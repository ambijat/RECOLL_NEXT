# Provenance and licensing preservation

## Project lineage

Recoll Next is an independent local product derived from the cloned Recoll source
history. The configured Git remote is historical metadata only and is not contacted.
Upstream history is preserved as lineage; new decisions, documentation, AI
integration, and local commits are made in this repository.

Inherited product manuals, generated documentation, citation metadata, and legacy
distribution packaging were intentionally removed to create a rebuild skeleton.
Their removal does not authorize removal of source notices, license texts, author
attribution, or third-party provenance required by retained code.

## Preserved legal artifacts

Material retained files include:

- `src/COPYING` and `src/AUTHORS`;
- component-specific `COPYING`, `LICENSE`, and `AUTHORS` files under retained source;
- Python binding and helper licenses;
- Qt single-application license;
- bundled third-party library notices;
- source-file copyright and license headers;
- `src/RECOLL-VERSION.txt` and `src/RECOLL-SOVERSION.txt`.

The repository contains multiple inherited components with their own terms. This
document is an engineering preservation protocol, not legal advice and not a
substitute for reading the applicable license files before distribution.

## Portability rules

- A source capsule includes all tracked license/provenance files.
- A source copy without `.git` loses material lineage evidence and is not Level S.
- Do not strip file headers during refactoring or skeletonization.
- Before deleting a retained directory, inspect it for unique license and attribution
  files and for build references.
- A binary/package checkpoint requires a generated inventory of included components,
  their source offers/notices as applicable, and destination-specific obligations.
- Model licenses and redistribution terms are separate from the application source;
  recording a model tag does not grant permission to redistribute its blobs.
- Corpus ownership and transfer authorization are external to the software license.

## New contributions

The governed source-distribution license is GPL-2.0-or-later, documented at the
repository root in `LICENSE.md`. New Recoll Next contributions use that license unless
a file carries a more specific compatible notice. Preserve commit authorship and do
not import third-party code or assets without recording origin, version, license, and
modification status.

Any future dependency manifest/SBOM must distinguish inherited source, new Recoll
Next code, runtime dependencies, model artifacts, and user corpus data.
