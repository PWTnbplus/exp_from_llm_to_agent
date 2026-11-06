# Publishing the public engineering release

This repository has two deliberately separate working trees:

- the research checkout contains protected evidence and local execution
  records;
- the generated public checkout contains only the `main` baseline plus the
  explicit public engineering allowlist.

Never publish the research checkout directly.

## Final local checks

From the generated public checkout, run:

```powershell
$env:PUBLIC_RELEASE_ROOT = "."
python -X utf8 scripts/check_environment.py
python -X utf8 scripts/reproduce.py --all --resume
python -X utf8 scripts/verify_results.py --all
python -X utf8 -m pytest -q
```

The offline artifacts must remain labeled `ENGINEERING_SMOKE_ONLY`; they are
not scientific results.

## Push and review

Use a GitHub account with write permission to the target repository:

```powershell
git remote add origin https://github.com/PWTnbplus/exp_from_llm_to_agent.git
git switch -c engineering/public-YYYYMMDD
git push -u origin engineering/public-YYYYMMDD
```

Then open a draft pull request from that branch into `main`. The pull request
should preserve the public-boundary scan and CI workflow. Do not merge or
force-push without human review.

The public branch must not contain raw runs, private data, credentials,
provider keys, or local archives. A real execution remains blocked unless the
protected inputs, authorization, budget, and model identity are supplied
explicitly outside this public release.
