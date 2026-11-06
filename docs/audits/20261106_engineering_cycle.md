# Engineering cycle audit — 2026-11-06

This is an engineering and release-boundary record. It is not a new scientific
result and does not replace the protected raw evidence or the existing audit
ledger.

## Changes made

- Added a machine-readable G0–G13 plus G8.5 registry with independent
  implementation, test, real-execution, and reproducibility states.
- Added an offline-first reproduction contract. Its artifacts are explicitly
  marked `ENGINEERING_SMOKE_ONLY`, `mock=true`, and `scientific_result=false`.
- Added per-experiment wrappers, schemas, contract tests, environment checks,
  result verification, and a public-release builder.
- Added public-boundary documentation, dependency metadata, citation metadata,
  and CI that runs without paid providers.
- Kept the existing G6–G8.5 and v7–v9 analysis code available to the public
  package while excluding protected data, raw runs, credentials, and local
  archives.

## Verified in the research checkout

- Full offline chain: all 15 registry entries produce and validate an
  engineering smoke artifact.
- Full test suite: `352 passed, 2 skipped in 49.48s`.
- The two skips are expected: the research checkout contains protected local
  evidence, and the V10 contract requires its completed-experiment paths.
- The research checkout intentionally fails the public-boundary scan because it
  contains local protected evidence. This is expected and is why publication is
  built from `main` plus an explicit allowlist.

## Release interpretation

The public package is a safe, executable engineering release. It does not
assert that G6, G7, G8, or G8.5 passed a scientific gate, and it does not make
G9–G13 publicly reproducible when their protected inputs are unavailable. The
registry is the source of truth for those distinctions.
