# Artifact retention policy

## Purpose

Keep the repository reviewable and reproducible without committing large, generated, proprietary, or credential-bearing outputs.

## Commit

- Source and test code, small deterministic fixtures, configuration, documentation, ADRs, and manifests.
- Concise machine-readable measurement summaries and exact reproduction commands.
- SHA-256 checksums and provenance/license records for external material that may legally be retained.
- Small decision-relevant reports that contain no restricted technology data.

## Do not commit

- Credentials, tokens, private keys, `.env` secrets, or vendor license files.
- Proprietary PDKs, foundry libraries, restricted board images, or material without verified redistribution permission.
- Tool databases, caches, waves, raw logs, bitstreams, FPGA databases, place-and-route trees, or temporary renders.
- Large checkpoints, datasets, traces, and binaries unless a later ADR selects an approved content-addressed store.

## Local layout

Generated outputs go under `artifacts/` by default and are ignored except for its README. Each stage retains a concise manifest in the applicable `docs/` area containing identity, checksums, tool versions, commands, summary metrics, and an approved external storage location when one exists.

## Promotion rule

An artifact may be promoted into Git only when it is required evidence, reviewable in size, reproducible or provenance-addressed, free of secrets/restricted data, and permitted by its license. The implementation status records each exception.

No artifact in this policy is evidence of NCA or Clef correctness unless the implementation status explicitly links it to a completed test.
