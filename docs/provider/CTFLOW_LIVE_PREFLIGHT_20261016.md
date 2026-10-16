# CTFlow live provider preflight

Date: 2026-10-17 Asia/Hong_Kong (`2026-10-16T16:35:58Z` recorded by the runner)

This is provider compatibility evidence only. It is not a scientific result and does not authorize a formal release.

## Documentation and endpoint

The provider documentation page was fetched over HTTPS from:

`https://token.ctflow.cn/tokendocs`

The page documents the following exact routes and authentication shape:

- API base: `https://token.ctflow.cn/v1`
- Chat route: `/chat/completions`
- Catalog route: `/models`
- Authentication: `Authorization: Bearer <local key>`

The page does not expose a verifiable per-model price table, token-usage billing contract, or machine-readable billing export endpoint. The project therefore does not claim that local token-price estimates are the provider bill.

## Live catalog and minimal generation preflight

Unauthenticated same-origin catalog probe: HTTP 401 (plausible protected catalog path).

Authenticated catalog discovery returned a parseable list of 243 exact model IDs. The selected IDs below were present in that live catalog. The key was read only from the local ignored `api_key/` tree and was never printed, persisted to a manifest, or included in logs.

| Exact model ID | Catalog | Minimal `chat/completions` preflight |
|---|---:|---:|
| `qwen3.5-plus` | present | PASS |
| `glm-5.2` | present | PASS |
| `deepseek-v3.2` | present | FAILED |

The preflight request used `stream=false`, `max_tokens=8`, and the existing short compatibility prompt. The failed DeepSeek model is excluded from any future formal selection until a separately authorized retry explains the failure.

## Budget and release decision

The user explicitly authorized paid model calls with an aggregate ceiling of USD 200. The two successful minimal preflight calls were the only new paid generation calls in this cycle.

Formal G0–G7 execution remains BLOCKED because:

1. CTFlow documentation does not provide independently verifiable pricing/billing evidence needed to claim that a local USD cap is a hard provider-spend cap.
2. The model-matrix scientific runner is not yet integrated: `runner_command=[]` and `runner_supports_budget_enforcement=false` remain intentional fail-closed settings.
3. Existing G7 formal input contracts are valid, but the real formal runner still requires independently auditable model snapshot and billing evidence; historical metadata is not an immutable weight snapshot and is not a billing receipt.

The explicit `$200` authorization is recorded in `configs/model_matrix.json`; it does not override these scientific and spending gates.
