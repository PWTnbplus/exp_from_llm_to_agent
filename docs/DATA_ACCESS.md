# Data access and public boundary

The public repository contains protocol definitions, source code, schemas, synthetic examples and audit methodology. It does not contain raw provider requests/responses, private ground truth, hidden holdouts, API keys, checkpoints, or local run caches.

Set `AI_SCIENTIFIC_REASONING_DATA_ROOT` to a controlled local data root when an authorized operator prepares real reproduction. The public entrypoint does not read this variable in offline mode.

Before any publication, run a tracked-file scan for `api_key/`, `runs/`, `private/`, `ground_truth_private/`, credentials and key/certificate extensions. `.gitignore` is not sufficient protection for files already in Git history; a public release must be built from an explicit allowlist.

Third-party components retain their original license and provenance. Do not redistribute a dataset or provider transcript without authorization.
